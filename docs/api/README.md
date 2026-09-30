# Contrato da API

[`openapi.yaml`](openapi.yaml) (OpenAPI 3.1) é o contrato da API de Logs e a fonte da verdade para backend, frontend e banco. Os três times desenvolvem em paralelo a partir dele.

## Como ver

- **Local:** `scripts/startup.sh` sobe o Swagger UI do contrato em http://127.0.0.1:8080. Ele lê o arquivo direto do repositório: depois de editar, basta recarregar a página.
- **Sem Docker:** abrir o arquivo em https://editor.swagger.io.

O Swagger em http://127.0.0.1:8000/docs é outro: é o gerado pelo FastAPI a partir do código. Os dois precisam descrever a mesma API; quando divergirem, vale o contrato.

## Status dos endpoints

| Endpoint | Status |
|---|---|
| `POST /auth/token`, `POST /logs` | Segue o documento do sistema (RN-01 a RN-16) |
| `POST /auth/login`, `GET /logs`, `GET /logs/{log_id}`, `/applications`, `/users`, `/customers` | **Proposta**: o documento põe cadastros e painel no escopo, mas não os detalha. Ver [Pontos em aberto](../../.ai/business-rules.md#pontos-em-aberto) |
| `GET /health` | Já implementado |
| Alertas | Fora do contrato até as regras serem definidas |

## Como o contrato está organizado

O contrato segue a separação por contexto e por agregado do domínio (Clean Architecture + DDD):

- **Um contexto por tag:** Autenticação, Ingestão de logs, Consulta de logs, Aplicações, Usuários, Clientes. Cada contexto tem o seu ator e a sua credencial, e uma credencial não serve em outro contexto (API key só emite token; token de aplicação só envia log; token de usuário só usa o painel).
- **Comandos separados de consultas:** a ingestão (`POST /logs`) escreve e não lê; o painel (`GET /logs`) lê e não escreve. Logs são imutáveis (RN-10).
- **Agregados como raiz dos caminhos:** `Application` é a raiz do agregado que contém as API keys, então as operações nas chaves passam por ela (`/applications/{application_id}/api-keys`). `Customer`, `User` e `Application` se ligam por id, nunca por objeto aninhado.
- **Operações com nome do domínio:** revogar uma chave é `POST .../revoke`, não um `DELETE` que na verdade não apaga.
- **DTOs separados do domínio e do banco:** um schema por papel (`LogCreate` entra, `LogRead` sai, igual aos modelos Pydantic de [standards.md](../../.ai/standards.md#modelos-pydantic-v2)). Nada da persistência vaza: nem `camelCase` do MongoDB, nem `key_hash`, `password_hash` ou `customer_id`.
- **Tenant implícito:** o cliente vem sempre da credencial (RN-01, RN-09). Não existe `customer_id` em corpo, parâmetro ou resposta; recurso de outro cliente responde 404.

## Backend

- Os modelos Pydantic têm os mesmos nomes e campos dos schemas (`LogCreate`, `LogRead`, `TokenResponse`, ...). Entrada com `ConfigDict(extra="forbid")`.
- Erros no formato Problem Details (RFC 9457). O 422 leva `errors` com `loc`, `msg` e `type`, o mesmo formato de `ValidationError.errors()` do Pydantic.
- Mudou endpoint, campo ou código de resposta? Primeiro o `openapi.yaml`, no mesmo PR do código.

## Frontend

- Gerar os tipos TypeScript a partir do contrato:
  ```bash
  cd frontend && npm run generate:api
  ```
- Enquanto o backend não implementa, usar um mock que responde com os exemplos do contrato:
  ```bash
  cd frontend && npm run mock   # http://127.0.0.1:4010
  ```
- O painel usa o token de usuário (`POST /auth/login`) no cabeçalho `Authorization: Bearer`. O token vale 1 hora e não tem renovação: expirou (401), volta para o login.

## Banco

O schema do MongoDB (validators, índices, tipos BSON e como o backend lê cada um) está em [`docs/database/README.md`](../database/README.md).

Campos do contrato → documentos do MongoDB (a conversão `snake_case` ↔ `camelCase` fica na camada de persistência):

| Contrato | MongoDB |
|---|---|
| `LogRead.id`, `ApplicationRead.id`, ... | `_id` (`ObjectId`) |
| `LogRead.application_id` | `logs.applicationId` |
| `LogRead.application_name` | `logs.applicationName` (cópia de `applications.name`) |
| `LogCreate.correlation_id` | `logs.correlationId` (UUID, `uuidRepresentation="standard"`) |
| `LogCreate.level` | `logs.level` (int) |
| `LogCreate.information_data` | `logs.informationData` (já mascarado) |
| `LogRead.tags` | `logs.tags` (lista final) |
| `LogCreate.occurred_at`, `LogRead.received_at`, `LogRead.expire_at` | `logs.occurredAt`, `logs.receivedAt`, `logs.expireAt` |
| `ApplicationRead.api_keys[].prefix`, `expires_at`, `revoked_at` | `applications.apiKeys[].prefix`, `expiresAt`, `revokedAt` |
| `CustomerRead.is_active`, `retention_days` | `customers.isActive`, `customers.retentionDays` |
| Não saem da API | `logs.customerId`, `applications.customerId`, `users.customerId`, `applications.apiKeys[].keyHash`, `users.passwordHash` |

Consultas de cada endpoint:

| Endpoint | Coleção | Operação | Índice |
|---|---|---|---|
| `POST /auth/token` | `applications`, `customers` | `find_one` por `apiKeys.keyHash`; `find_one` por `_id` | `{ "apiKeys.keyHash": 1 }` único, parcial |
| `POST /auth/login` | `users`, `customers` | `find_one` por `email`; `find_one` por `_id` | `{ email: 1 }` único, sem diferenciar maiúsculas |
| `POST /logs` | `applications`, `customers`, `logs` | `find_one` por `_id`; `insert_one` | TTL `{ expireAt: 1 }` |
| `GET /logs` | `logs` | `find` por `customerId` + filtros, ordenado por `occurredAt` decrescente | Os de `logs` em [architecture.md](../../.ai/architecture.md#índices) |
| `GET /logs/{log_id}` | `logs` | `find_one` por `_id` e `customerId` | `_id` |
| `POST /applications`, `PATCH /applications/{id}` | `applications` | `insert_one` / `update_one` | `{ customerId: 1, name: 1 }` único, com collation sem diferença de maiúsculas |
| `GET /applications` | `applications` | `find` por `customerId` | O índice acima |
| `POST .../api-keys`, `POST .../revoke` | `applications` | `update_one` com `$push` / `$set` em `apiKeys.$.revokedAt` | `_id` |
| `POST /users` | `users` | `insert_one` | `{ email: 1 }` único |
| `GET /users` | `users` | `find` por `customerId` | `{ customerId: 1 }` |
| `POST /customers` | `customers`, `users` | dois `insert_one` | `{ email: 1 }` único |
| `GET` / `PATCH /customers/me` | `customers` | `find_one` / `update_one` por `_id` | `_id` |

`POST /customers` grava em duas coleções. O MongoDB do `compose.yaml` é um nó único, sem transações: se o segundo `insert_one` falhar (e-mail repetido), o cliente precisa ser removido, ou o e-mail checado antes.

## Validar o contrato

```bash
docker run --rm -v "$PWD:/spec" redocly/cli lint /spec/docs/api/openapi.yaml
```

O lint confere a estrutura e se os exemplos batem com os schemas. O único aviso esperado é `GET /health` sem resposta 4xx.
