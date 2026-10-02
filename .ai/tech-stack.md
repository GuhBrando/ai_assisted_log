# Tech stack

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complementos posteriores ao documento: PyJWT, para o token de acesso temporário; uv, Uvicorn e o ambiente local em Docker; contrato OpenAPI com Swagger UI.
> Padrões de código: [standards.md](standards.md) · Decisões de arquitetura: [architecture.md](architecture.md).

Só as tecnologias abaixo estão aprovadas. Adicionar uma biblioteca nova exige registrá-la aqui, e em [architecture.md](architecture.md) se ela mudar uma decisão.

## Stack aprovada

| Camada | Tecnologia | Versão | Papel |
|---|---|---|---|
| Linguagem | Python | 3.14 | — |
| Dependências | uv (`pyproject.toml` + `uv.lock`) | 0.12.20 | Declara, resolve e instala as dependências; o `uv.lock` fixa as versões exatas |
| API | FastAPI | 0.141.1 | Rotas, injeção de dependências, autenticação (`X-API-Key` e Bearer), Swagger |
| Servidor ASGI | Uvicorn | 0.54.0 | Roda a aplicação FastAPI no container |
| Validação | Pydantic | **v2** (2.13.5) | Modelos de entrada, documento e resposta; rejeita campos extras |
| Validação de e-mail | email-validator (extra `pydantic[email]`) | 2.3.0 | Exigido pelo `EmailStr` do `User` |
| Acesso a dados | PyMongo Async (`AsyncMongoClient`) | 4.18.2 (mínimo 4.13, API assíncrona estável) | Driver oficial do MongoDB |
| Banco | MongoDB | 8.0 (imagem `mongo:8.0`) | Documentos BSON, índices e TTL para retenção |
| Senhas | pwdlib + Argon2 (`pwdlib[argon2]`) | 0.3.1 | Hash das senhas dos usuários da plataforma |
| Tokens de acesso | PyJWT | 2.15.1 | Emitir e validar o JWT de 1 hora das aplicações (HS256) |
| Testes | pytest, httpx, Testcontainers (MongoDB) | a definir | Testes de endpoint contra um MongoDB real em Docker |
| Containers | Docker + Docker Compose v2 | — | Sobe a API, o MongoDB e o Swagger UI no ambiente local |
| Contrato da API | OpenAPI + Swagger UI (imagem `swaggerapi/swagger-ui`) | 3.1 / v5.33.0 | Contrato em `docs/api/openapi.yaml`, visualizado no Swagger UI |

As versões das bibliotecas Python são as travadas no `uv.lock`; o `pyproject.toml` declara só o mínimo aceito (`>=`). Para atualizar uma biblioteca, rodar `uv lock --upgrade-package <pacote>` e atualizar esta tabela no mesmo commit. A versão mínima do PyMongo é a primeira em que a API assíncrona saiu do beta.

## Frontend desktop

O frontend em `frontend/` usa `npm` e `package-lock.json`, separadamente do `uv.lock` do backend. As versões exatas são fixadas pelo lock.

| Camada | Tecnologia | Versão instalada | Papel |
|---|---|---|---|
| Runtime desktop | Electron | 44.5.0 | Janela, isolamento, IPC e cliente HTTP local |
| Empacotamento | Electron Forge + Webpack | 8.0.1 | Build e pacote Windows com Squirrel |
| Interface | React + React DOM | 19.3.0 | Tela de login e investigação |
| Linguagem | TypeScript | 5.9.3 | Tipagem do cliente e do IPC |
| Estado remoto | TanStack Query | 5.104.0 | Cache por filtros, cursor e detalhe |
| Contrato | openapi-typescript | 7.13.0 | Geração de `src/api/schema.d.ts` a partir de `docs/api/openapi.yaml` |
| Mock de desenvolvimento | Prism CLI | 5.14.2 | Proxy de validação OpenAPI em `127.0.0.1:4010`, com 1.600 logs determinísticos servidos por upstream local em `127.0.0.1:4011` |
| Verificação | Vitest, oxlint, oxfmt | 5.0.2 / 1.86.0 / 0.41.0 | Testes, lint e formatação |

O aplicativo em desenvolvimento usa apenas o Prism na porta 4010; o pacote Windows usa a API local fixa na porta 8000. O renderer não chama a API diretamente. O token de usuário fica em memória no processo principal. A versão inicial não persiste sessão e não possui atualização automática.

## Configuração obrigatória

### MongoDB

```python
from pymongo import AsyncMongoClient

client = AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True)
```

- `uuidRepresentation="standard"`: grava `UUID` (ex.: `correlation_id`) no formato padrão.
- `tz_aware=True`: datas são lidas sempre com fuso (UTC).

### Token de acesso

| Item | Valor |
|---|---|
| Segredo de assinatura | Variável de ambiente `JWT_SECRET`, com pelo menos 32 bytes aleatórios (no ambiente local, o `scripts/startup.sh` gera um no `.env`) |
| Algoritmo | `HS256` |
| Validade | 3600 segundos (1 hora), limitada à expiração da API key |
| Claims obrigatórias | `sub` (id da aplicação), `iat`, `exp`, `jti` |

## Ambiente local (Docker)

| Arquivo | Papel |
|---|---|
| `Dockerfile` | Imagem da API: `python:3.14-slim` + uv 0.12.20. Instala com `uv sync --locked --no-dev` e roda com um usuário sem root |
| `compose.yaml` | Serviços `api` e `mongo` (`mongo:8.0`, volume `mongo-data`), com healthcheck; `migrate`, que aplica o schema do MongoDB e termina antes de a API subir; e `swagger` (Swagger UI com `docs/api/openapi.yaml`). Portas publicadas só em `127.0.0.1` |
| `.env.example` | Modelo do `.env`: `API_PORT` (padrão 8000), `MONGO_PORT` (padrão 27017), `SWAGGER_PORT` (padrão 8080) e `JWT_SECRET` |
| `scripts/startup.sh` | Cria o `.env`, gera o `JWT_SECRET` se estiver vazio, sobe os serviços e espera ficarem no ar |

```bash
scripts/startup.sh               # sobe a API, o MongoDB e o Swagger UI do contrato (http://127.0.0.1:8080)
docker compose logs -f api       # acompanha os logs da API
docker compose run --rm migrate  # reaplica o schema do MongoDB
docker compose down              # para os serviços; com -v apaga também os dados do MongoDB
```

- A API e o `migrate` leem `MONGODB_URI` (o `compose.yaml` aponta para `mongodb://mongo:27017/log_api`); a API lê também o `JWT_SECRET`.
- O `migrate` usa a mesma imagem da API e roda `python -m app.infrastructure.mongodb.migrate`: cria as coleções com validator, collation e índices, e é idempotente. Se ele falhar, a API não sobe. Detalhes em [`docs/database/README.md`](../docs/database/README.md).
- `GET /health` faz um `ping` no MongoDB: 200 se ele responde, 503 se não. É o healthcheck do container da API.
- O Swagger UI em http://127.0.0.1:8080 mostra o contrato (`docs/api/openapi.yaml`); o de http://127.0.0.1:8000/docs é o gerado pelo FastAPI a partir do código.
- O MongoDB local roda sem autenticação. Serve só para desenvolvimento; por isso a porta fica presa em `127.0.0.1`.

## Não usar

| Biblioteca ou prática | Motivo | Usar no lugar |
|---|---|---|
| Motor | Descontinuado em favor do PyMongo Async | `pymongo.AsyncMongoClient` |
| Pydantic v1 e a API `class Config` | A stack usa Pydantic v2 | `model_config = ConfigDict(...)` |
| Mock do MongoDB em testes de endpoint (ex.: mongomock) | Não valida índices únicos nem TTL | Testcontainers com MongoDB real |
| Senha em texto ou hash rápido sem salt | Requisito de segurança | pwdlib + Argon2 |
| Time series collection para `logs` | O TTL vale para a coleção inteira; a retenção é por cliente | Coleção comum com índice TTL em `expireAt` |
| python-jose | Sem manutenção ativa; a documentação do FastAPI usa PyJWT | PyJWT |
| Algoritmo lido do cabeçalho do token ou `none` | Permite forjar tokens | `algorithms=["HS256"]` fixo no `jwt.decode` |
| `requirements.txt` e `pip install` direto | As dependências são geridas pelo uv | `uv add <pacote>`, que atualiza `pyproject.toml` e `uv.lock` |

## A definir

- Versões de pytest, httpx e Testcontainers (entram no grupo `dev` do `pyproject.toml`, fora da imagem).
- Plugin de testes assíncronos do pytest (ex.: pytest-asyncio ou o plugin do anyio).
- Algoritmo de hash das API keys (ver [ADR-008](architecture.md#adr-008--api-keys-guardadas-como-hash--prefixo)).
