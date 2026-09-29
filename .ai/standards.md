# Padrões de código e estilo

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Stack e versões: [tech-stack.md](tech-stack.md) · Decisões de arquitetura: [architecture.md](architecture.md) · Domínio e regras: [business-rules.md](business-rules.md).

## Geral

- Código em Python, assíncrono de ponta a ponta: rotas `async def` e acesso ao banco pelo `AsyncMongoClient`. Não fazer chamadas síncronas ao banco dentro das rotas.
- Usar o vocabulário do domínio nos identificadores: `Customer`, `User`, `Application`, `ApiKey`, `LogCreate`, `LogDocument`, `LogRead`, `LogLevel`, `LogService`, `get_application`. Não criar sinônimos.
- `User` é a pessoa que usa a plataforma de logs, não o usuário final do sistema do cliente. Não misturar os dois conceitos em nomes ou modelos.

## Nomenclatura

| Onde | Convenção | Exemplo |
|---|---|---|
| Atributos Python e modelos Pydantic | `snake_case` | `correlation_id`, `information_data`, `occurred_at` |
| Campos nos documentos MongoDB | `camelCase` | `customerId`, `occurredAt`, `expireAt`, `apiKeys.keyHash` |
| Coleções MongoDB | plural, minúsculas | `customers`, `users`, `applications`, `logs` |
| Classes | `PascalCase` | `LogDocument`, `ApiKey` |
| Membros do enum de nível | maiúsculas | `LogLevel.WARNING` |

A conversão `snake_case` ↔ `camelCase` fica na camada de persistência. O resto do código usa só os nomes Python.

> A convenção de nomes do JSON da API ainda não foi definida. Ver [Pontos em aberto](business-rules.md#pontos-em-aberto).

## Camadas e responsabilidades

| Camada | Faz | Não faz |
|---|---|---|
| Rota FastAPI | Declara dependências, recebe `LogCreate`, devolve `LogRead` | Regra de negócio, acesso direto ao banco |
| Dependência `get_application` | Resolve `X-API-Key`, carrega `Application` e `Customer`, responde 401/403 | Validar o corpo |
| `LogService` | Regras de `information_data`, mascaramento, montagem do `LogDocument`, gravação | Autenticação |

- Toda rota autenticada por API key usa a dependência `get_application`.
- O ponto de entrada da ingestão é `LogService.registrar(log_create, application, customer)`.

## Modelos Pydantic (v2)

- Um modelo por papel:
  - `LogCreate`: o que o cliente envia.
  - `LogDocument`: o que é gravado; estende `LogCreate`.
  - `LogRead`: o que a API responde; `id` como `str`.
- Modelos de entrada usam `model_config = ConfigDict(extra="forbid")`. Um campo desconhecido gera 422 e nunca é ignorado em silêncio.
- Campos que só a API preenche (`id`, `customer_id`, `application_id`, `application_name`, `received_at`, `expire_at`) não existem no modelo de entrada.
- E-mail de usuário usa `EmailStr`.

## Tipos e dados

- **IDs:** `ObjectId` no banco, `str` nas respostas.
- **`correlation_id`:** `UUID`, gravado com `uuidRepresentation="standard"`.
- **Datas:** sempre com fuso, em UTC (`datetime.now(UTC)`). Nunca usar datas sem fuso nem `datetime.utcnow()`.
- **Nível:** gravar o valor numérico de `LogLevel`. Filtro por faixa é comparação: "a partir de Warning" é `level >= LogLevel.WARNING`.

## Acesso ao MongoDB

- Conectar com `AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True)`.
- **Toda consulta à coleção `logs` filtra por `customerId`.** Todo índice novo em `logs` começa por `customerId`.
- Em `logs` só existe `insert_one`. Não escrever `update` nem `delete`; quem apaga é o TTL.
- Não existe chave estrangeira: validar no código que o documento referenciado existe antes de gravar.
- Listagens de logs não usam `$lookup`; usam o `applicationName` copiado no próprio documento.
- Índices usados pela aplicação: [architecture.md](architecture.md#índices). Criar ou alterar um índice junto com o código que depende dele.

## Segurança no código

- Nunca gravar nem escrever em log de aplicação uma senha ou API key em texto. Senha vira `password_hash` (pwdlib + Argon2); API key vira hash + prefixo.
- O dono do log vem só da dependência de autenticação. Nunca ler `customer_id` ou `application_id` do corpo da requisição.
- Mascarar os campos sensíveis de `information_data` antes de gravar (regras em [business-rules.md](business-rules.md#rn-06--mascaramento-de-dados-sensíveis)).

## Erros HTTP

Usar os códigos da tabela [Códigos de resposta](business-rules.md#códigos-de-resposta). Não criar códigos diferentes para os mesmos casos.

## Testes

- Testes de endpoint com `pytest` + `httpx.AsyncClient` contra um MongoDB real subido pelo Testcontainers.
- Não mockar o MongoDB em teste de endpoint: mocks não validam os índices únicos nem o TTL.
- Cada regra de negócio tem pelo menos um teste. A lista mínima está em [Casos de aceitação](business-rules.md#casos-de-aceitação).
- Em testes de rejeição, verificar também que nada foi gravado (ex.: `customer_id` no corpo → 422 e coleção `logs` vazia).
