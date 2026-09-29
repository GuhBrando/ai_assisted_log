# Padrões de código e estilo

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complementos posteriores ao documento: tags, token de acesso temporário e dependências com uv.
> Stack e versões: [tech-stack.md](tech-stack.md) · Decisões de arquitetura: [architecture.md](architecture.md) · Domínio e regras: [business-rules.md](business-rules.md).

## Geral

- Código em Python, assíncrono de ponta a ponta: rotas `async def` e acesso ao banco pelo `AsyncMongoClient`. Não fazer chamadas síncronas ao banco dentro das rotas.
- Usar o vocabulário do domínio nos identificadores: `Customer`, `User`, `Application`, `ApiKey`, `AccessToken`, `LogCreate`, `LogDocument`, `LogRead`, `LogLevel`, `TokenResponse`, `LogService`, `TokenService`, `get_application`, `get_application_by_api_key`. Não criar sinônimos.
- `User` é a pessoa que usa a plataforma de logs, não o usuário final do sistema do cliente. Não misturar os dois conceitos em nomes ou modelos.

## Dependências e configuração

- Dependências só pelo uv: `uv add <pacote>`, ou `uv add --dev <pacote>` para as de teste. Não criar `requirements.txt` nem editar o `uv.lock` à mão.
- Biblioteca nova entra antes na [stack aprovada](tech-stack.md#stack-aprovada).
- `pyproject.toml` e `uv.lock` vão no mesmo commit. O build da imagem roda `uv sync --locked` e falha se o lock estiver desatualizado.
- Configuração vem de variáveis de ambiente (`MONGODB_URI`, `JWT_SECRET`). Segredos não ficam no código nem no `compose.yaml`, e o `.env` não vai para o repositório.
- O ambiente local sobe com `scripts/up.sh` (detalhes em [tech-stack.md](tech-stack.md#ambiente-local-docker)).

## Nomenclatura

| Onde | Convenção | Exemplo |
|---|---|---|
| Atributos Python e modelos Pydantic | `snake_case` | `correlation_id`, `information_data`, `occurred_at` |
| Campos nos documentos MongoDB | `camelCase` | `customerId`, `occurredAt`, `expireAt`, `apiKeys.keyHash` |
| Coleções MongoDB | plural, minúsculas | `customers`, `users`, `applications`, `logs` |
| Classes | `PascalCase` | `LogDocument`, `ApiKey` |
| Membros do enum de nível | maiúsculas | `LogLevel.WARNING` |
| Tags | `chave:valor` em minúsculas | `team:payments`, `feature:pix` |

A conversão `snake_case` ↔ `camelCase` fica na camada de persistência. O resto do código usa só os nomes Python.

> A convenção de nomes do JSON da API ainda não foi definida. Ver [Pontos em aberto](business-rules.md#pontos-em-aberto).

## Camadas e responsabilidades

| Camada | Faz | Não faz |
|---|---|---|
| Rota FastAPI | Declara dependências, recebe o corpo validado, devolve o modelo de resposta | Regra de negócio, acesso direto ao banco |
| Dependência `get_application_by_api_key` | Só em `POST /auth/token`: resolve `X-API-Key`, carrega `Application` e `Customer`, responde 401/403 | Ser usada no envio de logs |
| Dependência `get_application` | Em `POST /logs`: valida o Bearer token, carrega `Application` e `Customer`, responde 401/403 | Aceitar API key |
| `TokenService` | Gera e valida o JWT de 1 hora | Consultar o banco |
| `LogService` | Regras de `information_data`, mascaramento, junção das tags, montagem do `LogDocument`, gravação | Autenticação |

- Rotas de envio de logs usam `get_application` (token). Só `POST /auth/token` usa `get_application_by_api_key`.
- O ponto de entrada da ingestão é `LogService.registrar(log_create, application, customer)`.

## Modelos Pydantic (v2)

- Um modelo por papel:
  - `LogCreate`: o que o cliente envia.
  - `LogDocument`: o que é gravado; estende `LogCreate`.
  - `LogRead`: o que a API responde; `id` como `str`.
  - `TokenResponse`: resposta de `POST /auth/token`, com `access_token`, `token_type` e `expires_in`. São os nomes do OAuth 2.0 e ficam em `snake_case`, seja qual for a convenção do JSON da API.
- Modelos de entrada usam `model_config = ConfigDict(extra="forbid")`. Um campo desconhecido gera 422 e nunca é ignorado em silêncio.
- Campos que só a API preenche (`id`, `customer_id`, `application_id`, `application_name`, `received_at`, `expire_at`) não existem no modelo de entrada.
- Tags usam um tipo compartilhado entre `LogCreate` e `Application` (ex.: `Annotated[str, AfterValidator(normalizar_tag)]`). Ele remove os espaços das pontas, converte para minúsculas e valida o formato `chave:valor`. A lista é deduplicada e limitada no próprio modelo (regras em [RN-15](business-rules.md#rn-15--tags)).
- E-mail de usuário usa `EmailStr`.

## Tipos e dados

- **IDs:** `ObjectId` no banco, `str` nas respostas.
- **`correlation_id`:** `UUID`, gravado com `uuidRepresentation="standard"`.
- **Datas:** sempre com fuso, em UTC (`datetime.now(UTC)`). Nunca usar datas sem fuso nem `datetime.utcnow()`.
- **Nível:** gravar o valor numérico de `LogLevel`. Filtro por faixa é comparação: "a partir de Warning" é `level >= LogLevel.WARNING`.
- **Tags:** `list[str]` já normalizada. Nunca comparar nem filtrar tags sem passar pela mesma normalização.

## Acesso ao MongoDB

- Conectar com `AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True)`.
- **Toda consulta à coleção `logs` filtra por `customerId`.** Todo índice novo em `logs` começa por `customerId`.
- Filtro por tags usa `$all` junto com o cliente: `{"customerId": ..., "tags": {"$all": [...]}}`.
- Em `logs` só existe `insert_one`. Não escrever `update` nem `delete`; quem apaga é o TTL.
- Não existe chave estrangeira: validar no código que o documento referenciado existe antes de gravar.
- Listagens de logs não usam `$lookup`; usam o `applicationName` e as `tags` copiados no próprio documento.
- Índices usados pela aplicação: [architecture.md](architecture.md#índices). Criar ou alterar um índice junto com o código que depende dele.

## Segurança no código

- Nunca gravar nem escrever em log de aplicação uma senha, API key ou token em texto. Senha vira `password_hash` (pwdlib + Argon2); API key vira hash + prefixo; o token não é gravado.
- O dono do log vem só da dependência de autenticação. Nunca ler `customer_id` ou `application_id` do corpo da requisição.
- Mascarar os campos sensíveis de `information_data` antes de gravar (regras em [business-rules.md](business-rules.md#rn-06--mascaramento-de-dados-sensíveis)).
- Tags não passam pelo mascaramento: nunca colocar dado pessoal em tag, nem em exemplos e testes.

### Tokens de acesso

- Assinar e validar com PyJWT, algoritmo `HS256`, usando o segredo da variável de ambiente `JWT_SECRET`. O segredo nunca fica no código.
- Em `jwt.decode`, passar `algorithms=["HS256"]` e exigir `exp`, `iat` e `sub`. Nunca aceitar o algoritmo indicado pelo próprio token.
- Validade: `exp = min(iat + 3600 s, expires_at da API key)`. A duração fica em uma constante de configuração, não espalhada pelo código.
- A resposta de `POST /auth/token` leva `Cache-Control: no-store`. Respostas 401 de rotas com Bearer levam `WWW-Authenticate: Bearer`.

## Erros HTTP

Usar os códigos da tabela [Códigos de resposta](business-rules.md#códigos-de-resposta). Não criar códigos diferentes para os mesmos casos.

## Testes

- Testes de endpoint com `pytest` + `httpx.AsyncClient` contra um MongoDB real subido pelo Testcontainers.
- Não mockar o MongoDB em teste de endpoint: mocks não validam os índices únicos nem o TTL.
- Cada regra de negócio tem pelo menos um teste. A lista mínima está em [Casos de aceitação](business-rules.md#casos-de-aceitação).
- Em testes de rejeição, verificar também que nada foi gravado (ex.: `customer_id` no corpo → 422 e coleção `logs` vazia).
- Tokens expirados ou adulterados são gerados direto no teste (ex.: `exp` no passado, assinatura com outro segredo), sem esperar o tempo passar.
