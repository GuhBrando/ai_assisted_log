# Tech stack

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complementos posteriores ao documento: PyJWT, para o token de acesso temporário; uv, Uvicorn e o ambiente local em Docker.
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
| Containers | Docker + Docker Compose v2 | — | Sobe a API e o MongoDB no ambiente local |

As versões das bibliotecas Python são as travadas no `uv.lock`; o `pyproject.toml` declara só o mínimo aceito (`>=`). Para atualizar uma biblioteca, rodar `uv lock --upgrade-package <pacote>` e atualizar esta tabela no mesmo commit. A versão mínima do PyMongo é a primeira em que a API assíncrona saiu do beta.

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
| Segredo de assinatura | Variável de ambiente `JWT_SECRET`, com pelo menos 32 bytes aleatórios (no ambiente local, o `scripts/up.sh` gera um no `.env`) |
| Algoritmo | `HS256` |
| Validade | 3600 segundos (1 hora), limitada à expiração da API key |
| Claims obrigatórias | `sub` (id da aplicação), `iat`, `exp`, `jti` |

## Ambiente local (Docker)

| Arquivo | Papel |
|---|---|
| `Dockerfile` | Imagem da API: `python:3.14-slim` + uv 0.12.20. Instala com `uv sync --locked --no-dev` e roda com um usuário sem root |
| `compose.yaml` | Serviços `api` e `mongo` (`mongo:8.0`, volume `mongo-data`), com healthcheck. Portas publicadas só em `127.0.0.1` |
| `.env.example` | Modelo do `.env`: `API_PORT` (padrão 8000), `MONGO_PORT` (padrão 27017) e `JWT_SECRET` |
| `scripts/up.sh` | Cria o `.env`, gera o `JWT_SECRET` se estiver vazio, sobe os dois serviços e espera ficarem saudáveis |

```bash
scripts/up.sh                # sobe a API e o MongoDB (Swagger em http://127.0.0.1:8000/docs)
docker compose logs -f api   # acompanha os logs da API
docker compose down          # para os serviços; com -v apaga também os dados do MongoDB
```

- A API lê `MONGODB_URI` (o `compose.yaml` aponta para `mongodb://mongo:27017/log_api`) e `JWT_SECRET`.
- `GET /health` faz um `ping` no MongoDB: 200 se ele responde, 503 se não. É o healthcheck do container da API.
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
