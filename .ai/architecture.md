# Arquitetura

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complementos posteriores ao documento: tags (ADR-015), token de acesso temporário (ADR-016) e contrato da API (ADR-017 a ADR-019).
> Stack e versões: [tech-stack.md](tech-stack.md) · Padrões de código: [standards.md](standards.md) · Domínio e regras: [business-rules.md](business-rules.md).

## Visão geral

API multi-cliente que recebe, por um único endpoint (`POST /logs`), os logs enviados pelas aplicações de qualquer cliente e os guarda isolados por cliente.

A aplicação troca a sua API key por um token de acesso de 1 hora (`POST /auth/token`) e envia os logs com esse token no cabeçalho `Authorization: Bearer`. O cliente e a aplicação donos do log vêm dessa credencial, nunca de um campo do corpo.

Escopo desta versão: ingestão de logs, cadastro de clientes, aplicações e usuários, retenção automática por cliente, painel de consulta de logs e alertas. Complementos: tags em aplicações e logs, token de acesso de 1 hora.

## Componentes

```
App do cliente
  │
  ├─ 1. POST /auth/token (X-API-Key) ─▶ get_application_by_api_key ─▶ MongoDB: applications, customers
  │                                     TokenService ───────────────▶ JWT de 1 hora (não é gravado)
  │
  └─ 2. POST /logs (Bearer + JSON) ───▶ get_application ───────────▶ MongoDB: applications, customers
                                        LogService ────────────────▶ MongoDB: logs
                                                                      └─ monitor TTL apaga vencidos
```

| Componente | Responsabilidade |
|---|---|
| Rota `POST /auth/token` | Troca a API key por um token de acesso e devolve `TokenResponse` |
| Dependência `get_application_by_api_key` | Autentica a API key e carrega `Application` + `Customer` |
| `TokenService` | Gera e valida o JWT de 1 hora |
| Rota `POST /logs` | Valida o corpo como `LogCreate` (Pydantic) e devolve `LogRead` |
| Dependência `get_application` | Valida o token e carrega `Application` + `Customer` |
| `LogService` | Valida `information_data`, mascara dados sensíveis, junta as tags, monta o `LogDocument` e grava |
| MongoDB | Persistência, índices e remoção de logs vencidos por TTL |

## Fluxo de emissão do token (`POST /auth/token`)

1. O app do cliente envia `POST /auth/token` com o cabeçalho `X-API-Key`.
2. A dependência `get_application_by_api_key` calcula o hash da chave recebida.
3. Busca a aplicação: `applications.find_one` por `apiKeys.keyHash`.
4. Chave ausente, inexistente, expirada ou revogada → **401 Unauthorized**.
5. Busca o cliente: `customers.find_one` por `customerId` (resultado pode ficar em cache). Cliente inativo → **403 Forbidden**.
6. O `TokenService` gera o JWT com `sub` (id da aplicação), `iat`, `exp = min(iat + 1 hora, expiresAt da chave)` e `jti`.
7. A API responde **200 OK** com `access_token`, `token_type: "bearer"` e `expires_in`, e o cabeçalho `Cache-Control: no-store`.

## Fluxo de ingestão (`POST /logs`)

1. O app do cliente envia `POST /logs` com o cabeçalho `Authorization: Bearer <token>` e o corpo JSON.
2. O FastAPI resolve a dependência `get_application`.
3. A dependência valida a assinatura e a expiração do token. Ausente, inválido ou expirado → **401 Unauthorized** (com `WWW-Authenticate: Bearer`).
4. Busca a aplicação por `_id` igual ao `sub` do token (resultado pode ficar em cache). Não encontrada → **401**.
5. Busca o cliente por `customerId` (resultado pode ficar em cache). Cliente inativo → **403 Forbidden**.
6. O Pydantic valida o corpo como `LogCreate`, incluindo o formato e o limite das tags. Campo inválido ou extra (como `customer_id`) → **422 Unprocessable Entity**.
7. A rota chama `LogService.registrar(log_create, application, customer)`.
8. O serviço checa o tamanho e as chaves de `information_data`: acima do limite → **413 Payload Too Large**; chave com `$` ou `.` → **422**.
9. O serviço mascara os campos sensíveis (senha, CPF, cartão).
10. O serviço junta as tags da aplicação com as do log; nas chaves que a aplicação define, vale a da aplicação.
11. O serviço monta o `LogDocument` com `received_at`, `expire_at`, `application_name` e as tags finais.
12. `logs.insert_one` devolve o `inserted_id`.
13. A API responde **201 Created** com o `LogRead` (id do log).
14. Depois de `expireAt`, o monitor TTL do MongoDB apaga o documento.

## Contrato da API

O contrato fica em [`docs/api/openapi.yaml`](../docs/api/openapi.yaml) (OpenAPI 3.1) e é a fonte da verdade da API (ADR-017). Guia por time em [`docs/api/README.md`](../docs/api/README.md).

| Contexto | Endpoints | Credencial | Status |
|---|---|---|---|
| Autenticação | `POST /auth/token` | API key (`X-API-Key`) | Documento do sistema |
| Autenticação | `POST /auth/login` | E-mail e senha | Proposta |
| Ingestão de logs | `POST /logs` | Token de aplicação | Documento do sistema |
| Consulta de logs | `GET /logs`, `GET /logs/{log_id}` | Token de usuário | Proposta |
| Aplicações | `/applications`, `/applications/{application_id}/api-keys`, `.../api-keys/{prefix}/revoke` | Token de usuário | Proposta |
| Usuários | `/users`, `/users/me`, `/users/{user_id}` | Token de usuário | Proposta |
| Clientes | `POST /customers` (sem credencial), `/customers/me` | Token de usuário | Proposta |
| Operação | `GET /health` | Nenhuma | Implementado |

Os endpoints marcados como proposta cobrem o escopo (cadastros e painel), que o documento não detalha. As decisões que eles pedem estão em [Pontos em aberto](business-rules.md#pontos-em-aberto).

## Persistência (MongoDB)

Quatro coleções: `customers`, `users`, `applications` e `logs`. As API keys ficam embutidas no array `apiKeys` de cada documento de `applications`; as demais relações são referências por `ObjectId`. Como o MongoDB não tem chave estrangeira, a integridade é garantida pela API. Tokens de acesso não são gravados (ADR-016).

| Coleção | Campos |
|---|---|
| `customers` | `_id`, `name`, `isActive`, `retentionDays`, `createdAt` |
| `users` | `_id`, `customerId`, `name`, `email` (único), `passwordHash`, `createdAt` |
| `applications` | `_id`, `customerId`, `name`, `apiKeys` (array de subdocumentos), `tags` (array de strings `chave:valor`), `createdAt` |
| `applications.apiKeys[]` | `keyHash` (único), `prefix`, `expiresAt`, `revokedAt` |
| `logs` | `_id`, `customerId`, `applicationId`, `applicationName` (cópia de `applications.name`), `correlationId` (UUID, opcional), `level` (int), `message`, `exception` (opcional), `environment`, `informationData` (documento livre, opcional), `tags` (array de strings `chave:valor`, lista final), `occurredAt`, `receivedAt`, `expireAt` |

### Índices

| Coleção | Índice | Uso |
|---|---|---|
| `users` | `{ email: 1 }` único | Login e unicidade do e-mail |
| `applications` | `{ "apiKeys.keyHash": 1 }` único | Autenticação da API key na emissão do token |
| `logs` | `{ customerId: 1, occurredAt: -1 }` | Listagem padrão, mais recentes primeiro |
| `logs` | `{ customerId: 1, correlationId: 1 }` | Rastrear um fluxo completo |
| `logs` | `{ customerId: 1, applicationId: 1, level: 1, occurredAt: -1 }` | Filtros combinados |
| `logs` | `{ customerId: 1, tags: 1, occurredAt: -1 }` | Filtro por tags (índice multikey) |
| `logs` | `{ expireAt: 1 }` com `expireAfterSeconds: 0` | Apagar logs vencidos (TTL) |

## Decisões (ADRs)

| ADR | Decisão |
|---|---|
| [001](#adr-001--cliente-identificado-pela-credencial-da-aplicação) | Cliente identificado pela credencial da aplicação |
| [002](#adr-002--mongodb-com-pymongo-async) | MongoDB com PyMongo Async |
| [003](#adr-003--embutir-ou-referenciar) | Embutir ou referenciar |
| [004](#adr-004--retenção-por-ttl-em-cada-documento) | Retenção por TTL em cada documento |
| [005](#adr-005--aplicação-como-entidade) | Aplicação como entidade |
| [006](#adr-006--usuário-vinculado-ao-cliente) | Usuário vinculado ao cliente |
| [007](#adr-007--senhas-com-pwdlib--argon2) | Senhas com pwdlib + Argon2 |
| [008](#adr-008--api-keys-guardadas-como-hash--prefixo) | API keys guardadas como hash + prefixo |
| [009](#adr-009--objectid-como-id-do-log) | `ObjectId` como id do log |
| [010](#adr-010--duas-datas-no-log) | Duas datas no log |
| [011](#adr-011--loglevel-numérico-com-seis-valores) | `LogLevel` numérico com seis valores |
| [012](#adr-012--information_data-com-limite-e-mascaramento) | `information_data` com limite e mascaramento |
| [013](#adr-013--logs-imutáveis) | Logs imutáveis |
| [014](#adr-014--testes-contra-mongodb-real) | Testes contra MongoDB real |
| [015](#adr-015--tags-como-dimensão-de-filtro) | Tags como dimensão de filtro |
| [016](#adr-016--token-de-acesso-temporário-jwt-de-1-hora) | Token de acesso temporário (JWT de 1 hora) |
| [017](#adr-017--contrato-openapi-como-fonte-da-verdade) | Contrato OpenAPI como fonte da verdade |
| [018](#adr-018--json-da-api-em-snake_case) | JSON da API em `snake_case` |
| [019](#adr-019--erros-no-formato-problem-details-rfc-9457) | Erros no formato Problem Details (RFC 9457) |

Todas com status **Aceita**.

### ADR-001 — Cliente identificado pela credencial da aplicação

- **Contexto:** o modelo original recebia `CustomerId` no corpo, o que permitia gravar logs em nome de outro cliente.
- **Decisão:** cliente e aplicação donos do log vêm só da credencial da aplicação: a API key na emissão do token e o token de acesso no envio de logs (ADR-016). `LogCreate` usa `ConfigDict(extra="forbid")`, então um `customer_id` no corpo é recusado com 422 em vez de ser ignorado.
- **Consequências:** o envio de logs depende da dependência `get_application`; nenhum campo do corpo troca o dono do log.

### ADR-002 — MongoDB com PyMongo Async

- **Contexto:** a API é assíncrona (FastAPI) e grava no MongoDB.
- **Decisão:** usar o driver oficial assíncrono do PyMongo (`AsyncMongoClient`). O Motor foi descontinuado em favor dele.
- **Consequências:** sem chave estrangeira, a integridade referencial é responsabilidade da API. A conexão usa `uuidRepresentation="standard"` e `tz_aware=True`.

### ADR-003 — Embutir ou referenciar

| Relação | Decisão | Motivo |
|---|---|---|
| Application → ApiKey | Embutida | Poucas por aplicação e sempre lidas junto com ela |
| Customer → Application | Referência | A aplicação é consultada sozinha a cada requisição |
| Customer → User | Referência | Se um usuário precisar atender vários clientes, vira um array `customerIds` |
| Log → Customer / Application | Referência + cópia do nome | Listagens e filtros não precisam de `$lookup` |
| Log → tags da aplicação | Cópia | O filtro por tags consulta só a coleção `logs` |

### ADR-004 — Retenção por TTL em cada documento

- **Contexto:** cada cliente define o próprio prazo de retenção (`retentionDays`).
- **Decisão:** ao inserir, a API calcula `expireAt = receivedAt + retentionDays` do cliente. Um índice TTL em `expireAt` com `expireAfterSeconds: 0` faz o MongoDB apagar o documento depois dessa data.
- **Alternativa descartada:** time series collection. Comprimiria melhor, mas o TTL dela vale para a coleção inteira, o que impede um prazo por cliente.
- **Consequências:** cada cliente tem seu prazo, e logs não ficam para sempre (princípio de necessidade da LGPD).

### ADR-005 — Aplicação como entidade

- **Contexto:** o modelo original tinha `ApplicationName` como texto livre, o que permitia "Checkout" e "checkout" como aplicações diferentes.
- **Decisão:** entidade `Application`, dona das API keys; o nome é copiado no log (`applicationName`).

### ADR-006 — Usuário vinculado ao cliente

- **Contexto:** no modelo original, `User` não tinha vínculo com cliente.
- **Decisão:** `User.customerId`, para que cada usuário veja só os logs do seu cliente.
- **Em aberto:** se um usuário puder atender mais de um cliente, `customerId` vira `customerIds` (ver [Pontos em aberto](business-rules.md#pontos-em-aberto)).

### ADR-007 — Senhas com pwdlib + Argon2

- **Contexto:** o modelo original guardava `password`.
- **Decisão:** guardar só `password_hash`, gerado com pwdlib + Argon2. Senha nunca fica em texto.

### ADR-008 — API keys guardadas como hash + prefixo

- **Decisão:** a plataforma gera a chave e a mostra uma única vez. O banco guarda só o hash e um prefixo curto (ex.: `lx_ab12`) para identificação. Uma aplicação pode ter várias chaves, e cada uma expira ou é revogada sem afetar as outras.
- **Consequências:** a emissão do token (ADR-016) busca a aplicação pelo hash da chave recebida, usando o índice único `apiKeys.keyHash`. Por isso esse hash precisa ser determinístico, ao contrário do hash de senha. O algoritmo ainda não foi definido (ver [Pontos em aberto](business-rules.md#pontos-em-aberto)).

### ADR-009 — `ObjectId` como id do log

- **Contexto:** o modelo original usava `LogId` inteiro.
- **Decisão:** `ObjectId`, o padrão do MongoDB, gerado sem consultar o banco. Nas respostas (`LogRead`), o id vai como texto.

### ADR-010 — Duas datas no log

- **Contexto:** o log original não tinha data.
- **Decisão:** `occurred_at` (quando o evento aconteceu no cliente) e `received_at` (quando chegou à API, preenchido pela API).

### ADR-011 — `LogLevel` numérico com seis valores

- **Contexto:** o modelo original tinha três níveis.
- **Decisão:** `IntEnum` com seis valores (Trace 0 a Critical 5). Separa erro tratado de falha crítica e permite filtrar por faixa (`level >= 3`).

### ADR-012 — `information_data` com limite e mascaramento

- **Contexto:** o modelo original tinha `InformationData` como objeto livre, e o cliente pode enviar o request inteiro.
- **Decisão:** documento BSON com limite de tamanho, recusa de chaves com `$` ou `.` e mascaramento de campos sensíveis antes de gravar.
- **Consequências:** protege dados sensíveis e o tamanho do banco.

### ADR-013 — Logs imutáveis

- **Decisão:** logs só são inseridos. Não existe endpoint de alteração; a remoção acontece só pelo TTL.

### ADR-014 — Testes contra MongoDB real

- **Decisão:** testes de endpoint com pytest e `httpx.AsyncClient` contra um MongoDB real subido pelo Testcontainers.
- **Motivo:** mocks não validariam os índices únicos nem o TTL.

### ADR-015 — Tags como dimensão de filtro

- **Contexto:** os filtros do documento (cliente, aplicação, nível, período e `correlationId`) não cobrem recortes como time, funcionalidade ou região.
- **Decisão:** campo `tags`, um array de strings `chave:valor` normalizadas em minúsculas, em `applications` e em `logs`. Ao gravar, o log recebe as tags da aplicação somadas às dele; nas chaves que a aplicação define, vale a da aplicação. Índice multikey `{ customerId: 1, tags: 1, occurredAt: -1 }`.
- **Alternativas descartadas:**
  - Objeto `{ chave: valor }`: aceita um só valor por chave e, com chaves livres, exige índice curinga (`$**`).
  - Array de `{ k, v }` (attribute pattern): filtra igual, mas as consultas com `$elemMatch` ficam mais verbosas.
- **Consequências:** o filtro por tags usa `$all` e não precisa de `$lookup`. Mudar as tags de uma aplicação não altera logs já gravados. Tags ficam fora do mascaramento, então não podem conter dados pessoais.

### ADR-016 — Token de acesso temporário (JWT de 1 hora)

- **Contexto:** a API key é uma credencial de longa duração. Enviada em todo log, ela fica mais exposta (código do cliente, proxies, logs de rede).
- **Decisão:** `POST /auth/token` troca a API key por um JWT assinado com HS256, válido por 1 hora e nunca além da expiração da chave. `POST /logs` aceita só `Authorization: Bearer <token>`. Claims: `sub` (id da aplicação), `iat`, `exp` e `jti`. O token não é gravado.
- **Alternativa descartada:** token opaco guardado no MongoDB com índice TTL. Permitiria revogação imediata, mas exige uma coleção nova e uma consulta a mais em cada envio de log.
- **Consequências:**
  - Revogar uma API key impede novos tokens, mas não derruba os já emitidos (no máximo 1 hora). Está nos [Pontos em aberto](business-rules.md#pontos-em-aberto).
  - Desativar o cliente vale na hora, porque o cliente é checado em cada envio.
  - O segredo de assinatura (`JWT_SECRET`) vira uma credencial crítica da plataforma. Trocá-lo invalida todos os tokens emitidos.
  - A aplicação cliente precisa pedir um novo token antes de o atual expirar.

### ADR-017 — Contrato OpenAPI como fonte da verdade

- **Contexto:** backend, frontend e banco precisam desenvolver em paralelo, antes de a API existir.
- **Decisão:** o contrato é escrito primeiro, à mão, em `docs/api/openapi.yaml` (OpenAPI 3.1). Mudança de endpoint, campo ou código de resposta começa no contrato, no mesmo PR do código. O `compose.yaml` sobe um Swagger UI com ele.
- **Alternativa descartada:** usar só o OpenAPI que o FastAPI gera do código. Ele só existe depois da implementação, e o que o código faz vira o contrato sem revisão.
- **Consequências:** o OpenAPI gerado pelo FastAPI (`/docs`) precisa bater com o contrato; quando divergirem, vale o contrato. O frontend gera tipos e mocks a partir dele.

### ADR-018 — JSON da API em `snake_case`

- **Contexto:** o documento do sistema usava `correlationId` na visão geral e `customer_id` nos exemplos de payload.
- **Decisão:** corpos, parâmetros e respostas em `snake_case`, com os mesmos nomes dos atributos Python.
- **Motivo:** os modelos Pydantic já usam `snake_case`, então não há aliases para manter; os exemplos do documento e o `TokenResponse` (OAuth 2.0) já estavam assim.
- **Consequências:** o `camelCase` fica só nos documentos do MongoDB, convertido na camada de persistência.

### ADR-019 — Erros no formato Problem Details (RFC 9457)

- **Decisão:** toda resposta de erro usa `application/problem+json` com `type`, `title`, `status` e `detail`. O 422 acrescenta `errors`, uma lista com `loc`, `msg` e `type`, no formato dos erros do Pydantic.
- **Motivo:** um formato padrão e único de erro para todos os endpoints, que o frontend trata em um lugar só.
- **Consequências:** o backend troca os handlers de erro padrão do FastAPI, que respondem `{"detail": ...}`.
