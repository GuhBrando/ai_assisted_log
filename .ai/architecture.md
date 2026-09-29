# Arquitetura

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Stack e versões: [tech-stack.md](tech-stack.md) · Padrões de código: [standards.md](standards.md) · Domínio e regras: [business-rules.md](business-rules.md).

## Visão geral

API multi-cliente que recebe, por um único endpoint (`POST /logs`), os logs enviados pelas aplicações de qualquer cliente e os guarda isolados por cliente. O cliente é identificado pela API key enviada no cabeçalho `X-API-Key`, nunca por um campo do corpo.

Escopo desta versão: ingestão de logs, cadastro de clientes, aplicações e usuários, retenção automática por cliente, painel de consulta de logs e alertas.

## Componentes

```
App do cliente ──POST /logs (X-API-Key + JSON)──▶ FastAPI
                                                   │
                                                   ├─▶ get_application ──▶ MongoDB: applications, customers
                                                   │
                                                   └─▶ LogService ───────▶ MongoDB: logs
                                                                             └─ monitor TTL apaga vencidos
```

| Componente | Responsabilidade |
|---|---|
| Rota FastAPI `POST /logs` | Valida o corpo como `LogCreate` (Pydantic) e devolve `LogRead` |
| Dependência `get_application` | Autentica a API key e carrega `Application` + `Customer` |
| `LogService` | Valida `information_data`, mascara dados sensíveis, monta o `LogDocument` e grava |
| MongoDB | Persistência, índices e remoção de logs vencidos por TTL |

## Fluxo de ingestão (`POST /logs`)

1. O app do cliente envia `POST /logs` com o cabeçalho `X-API-Key` e o corpo JSON.
2. O FastAPI resolve a dependência `get_application`.
3. A dependência calcula o hash da chave recebida.
4. Busca a aplicação: `applications.find_one` por `apiKeys.keyHash`.
5. Chave inexistente, expirada ou revogada → **401 Unauthorized**.
6. Busca o cliente: `customers.find_one` por `customerId`. Esse resultado pode ficar em cache.
7. Cliente inativo → **403 Forbidden**.
8. O Pydantic valida o corpo como `LogCreate`. Campo inválido ou extra (como `customer_id`) → **422 Unprocessable Entity**.
9. A rota chama `LogService.registrar(log_create, application, customer)`.
10. O serviço checa o tamanho e as chaves de `information_data`: acima do limite → **413 Payload Too Large**; chave com `$` ou `.` → **422**.
11. O serviço mascara os campos sensíveis (senha, CPF, cartão).
12. O serviço monta o `LogDocument` com `received_at`, `expire_at` e `application_name`.
13. `logs.insert_one` devolve o `inserted_id`.
14. A API responde **201 Created** com o `LogRead` (id do log).
15. Depois de `expireAt`, o monitor TTL do MongoDB apaga o documento.

## Persistência (MongoDB)

Quatro coleções: `customers`, `users`, `applications` e `logs`. As API keys ficam embutidas no array `apiKeys` de cada documento de `applications`; as demais relações são referências por `ObjectId`. Como o MongoDB não tem chave estrangeira, a integridade é garantida pela API.

| Coleção | Campos |
|---|---|
| `customers` | `_id`, `name`, `isActive`, `retentionDays`, `createdAt` |
| `users` | `_id`, `customerId`, `name`, `email` (único), `passwordHash`, `createdAt` |
| `applications` | `_id`, `customerId`, `name`, `apiKeys` (array de subdocumentos), `createdAt` |
| `applications.apiKeys[]` | `keyHash` (único), `prefix`, `expiresAt`, `revokedAt` |
| `logs` | `_id`, `customerId`, `applicationId`, `applicationName` (cópia de `applications.name`), `correlationId` (UUID, opcional), `level` (int), `message`, `exception` (opcional), `environment`, `informationData` (documento livre, opcional), `occurredAt`, `receivedAt`, `expireAt` |

### Índices

| Coleção | Índice | Uso |
|---|---|---|
| `users` | `{ email: 1 }` único | Login e unicidade do e-mail |
| `applications` | `{ "apiKeys.keyHash": 1 }` único | Autenticação de cada requisição |
| `logs` | `{ customerId: 1, occurredAt: -1 }` | Listagem padrão, mais recentes primeiro |
| `logs` | `{ customerId: 1, correlationId: 1 }` | Rastrear um fluxo completo |
| `logs` | `{ customerId: 1, applicationId: 1, level: 1, occurredAt: -1 }` | Filtros combinados |
| `logs` | `{ expireAt: 1 }` com `expireAfterSeconds: 0` | Apagar logs vencidos (TTL) |

## Decisões (ADRs)

| ADR | Decisão |
|---|---|
| [001](#adr-001--cliente-identificado-pela-api-key) | Cliente identificado pela API key |
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

Todas com status **Aceita**.

### ADR-001 — Cliente identificado pela API key

- **Contexto:** o modelo original recebia `CustomerId` no corpo, o que permitia gravar logs em nome de outro cliente.
- **Decisão:** cliente e aplicação donos do log vêm só da API key. `LogCreate` usa `ConfigDict(extra="forbid")`, então um `customer_id` no corpo é recusado com 422 em vez de ser ignorado.
- **Consequências:** a ingestão depende da dependência `get_application`; nenhum campo do corpo troca o dono do log.

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
- **Consequências:** a autenticação busca a aplicação pelo hash da chave recebida, usando o índice único `apiKeys.keyHash`. Por isso esse hash precisa ser determinístico, ao contrário do hash de senha. O algoritmo ainda não foi definido (ver [Pontos em aberto](business-rules.md#pontos-em-aberto)).

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
