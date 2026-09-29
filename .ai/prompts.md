# Prompts

Registro de cada prompt enviado a uma LLM para trabalhar neste repositório e do que foi executado. Regras e formato em [AGENTS.md](../AGENTS.md#registro-de-prompts).

Os prompts anteriores a este registro, que geraram as PRs #1 e #2, não foram registrados.

## 001 — Dockerfile e script para subir o ambiente

- **Data:** 2026-09-29
- **Branch:** `feat/docker-environment`
- **PR:** #3

**Prompt**

> Baseado nos .md em .ai eu quero que você crie uma PR adicionar o dockerfile com as imagens das tecnologias, rodando 100%. Nessa implementação também gostaria que gerasse um shell que subisse os pods do docker também para facilitar

**Executado**

- Leitura de `.ai/*.md`. O repositório ainda não tinha código, então foi criado um esqueleto mínimo para o container ter o que rodar: `app/main.py` (FastAPI) com `GET /health`, que faz `ping` no MongoDB pelo `AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True)`.
- Criados `Dockerfile` (`python:3.14-slim`, usuário sem root, healthcheck), `compose.yaml` (`api` + `mongo:8.0` com healthcheck, volume `mongo-data`, portas só em `127.0.0.1`), `.env.example`, `.dockerignore`, `.gitattributes` (`*.sh` com LF), `requirements.txt` com versões fixadas (trocado no 002) e `scripts/up.sh` (renomeado no 004), que cria o `.env`, gera o `JWT_SECRET` e roda `docker compose up -d --build --wait`.
- O Docker Desktop estava parado e foi iniciado.
- Verificação: build ok, containers `healthy`, `/health` 200, `/docs` 200. Dentro do container, hash Argon2, `EmailStr` e JWT HS256 funcionaram.
- Com o MongoDB parado, `/health` levava 33 s para responder 503. Corrigido com `pymongo.timeout(3)`.
- O usuário interrompeu durante a verificação e enviou o 002. Nada foi commitado neste prompt.

## 002 — uv e pyproject.toml no lugar do requirements.txt

- **Data:** 2026-09-29
- **Branch:** `feat/docker-environment`
- **PR:** #3

**Prompt**

> Atualize na documentação, utilize UV e pyproject.toml inves de requirements.txt para subir montar a aplicação python

**Executado**

- Removido `requirements.txt`. Criados `pyproject.toml` (versões mínimas com `>=`) e `uv.lock`, gerado com o uv 0.12.20 dentro de um container (o uv do host era o 0.9.7).
- `Dockerfile`: uv copiado de `ghcr.io/astral-sh/uv:0.12.20` e dependências instaladas com `uv sync --locked --no-dev`, numa camada separada do código.
- `.ai/tech-stack.md`: versões fixadas (Python 3.14, FastAPI 0.141.1, Pydantic 2.13.5, PyMongo 4.18.2, pwdlib 0.3.1, PyJWT 2.15.1, MongoDB 8.0), uv e Uvicorn na stack, seção "Ambiente local (Docker)" e `requirements.txt` em "Não usar".
- `.ai/standards.md`: seção "Dependências e configuração" (`uv add`, lock no mesmo commit, segredos só em variáveis de ambiente).
- Verificação: 22 pacotes instalados pelo lock; a API roda como `app` a partir do `/srv/.venv`; com o MongoDB parado, `/health` responde 503 em ~3 s e volta a 200 quando ele religa; rodar o script de novo mantém o `JWT_SECRET`; `uv sync --locked` falha quando o `pyproject.toml` muda sem atualizar o lock.
- Commit `e698ac1`, push e PR #3, com base em `docs/ai-context-from-system-doc` (empilhada sobre a #2).

## 003 — Contrato da API (Swagger) e AGENTS.md

- **Data:** 2026-09-29
- **Branch:** `feat/api-contract`, `docs/agents-prompt-log`
- **PR:** #5, #6

**Prompt**

> Fora isso eu gostaria tambem que criasse uma outra PR com um swagger com os contratos da API para que eu possa disponibilizar para o Backend, frontend e o banco poder desenvolver. Crie para mim respeitando a documentação e as boas praticas de clean arch e DDD. Fora isso gostaria que também criasse um AGENTS.md onde nele você passaria a orientação de a cada prompt enviado para uma LLM deve ser gravado em um arquivo no .ai. É um arquivo chamado prompts.md onde nele terá tudo que foi executado

**Executado**

- `docs/api/openapi.yaml` (OpenAPI 3.1): 19 operações em 7 contextos (Autenticação, Ingestão de logs, Consulta de logs, Aplicações, Usuários, Clientes, Operação), 3 esquemas de credencial (API key, token de aplicação, token de usuário), schemas por papel (`LogCreate`, `LogRead`, `TokenResponse`, ...), erros em Problem Details e exemplos. `POST /auth/token` e `POST /logs` seguem as RN-01 a RN-16; os endpoints de cadastro e painel, que o documento não detalha, ficaram marcados como proposta.
- `docs/api/README.md`: como ver o contrato, organização por contexto e agregado (Clean Architecture + DDD), guia para backend, frontend e banco, mapeamento dos campos para o MongoDB e as consultas de cada endpoint.
- Serviço `swagger` (`swaggerapi/swagger-ui:v5.33.0`) no `compose.yaml`, na porta `SWAGGER_PORT` (8080); `scripts/startup.sh` mostra a URL.
- `.ai/architecture.md`: seção "Contrato da API" e ADR-017 (contrato primeiro), ADR-018 (JSON em `snake_case`) e ADR-019 (Problem Details). `.ai/standards.md`, `.ai/business-rules.md` e `.ai/tech-stack.md` atualizados; as propostas do contrato foram para "Pontos em aberto".
- Verificação: `openapi-spec-validator` OK; `redocly lint` válido, com um aviso esperado (`GET /health` sem 4xx); um exemplo estragado de propósito foi apontado, o que confirma que os exemplos são validados contra os schemas; screenshot com Chrome headless mostrou o contrato renderizado no Swagger UI.
- Commit `f52b8c3`, push e PR #5, com base em `feat/docker-environment` (empilhada sobre a #3).
- Criados `AGENTS.md` (contexto do projeto e regras do registro de prompts) e este arquivo, com as entradas desta sessão. PR #6, com base em `main`.

## 004 — Renomear o script para startup.sh

- **Data:** 2026-09-29
- **Branch:** `feat/docker-environment`
- **PR:** #3

**Prompt**

> mude o nome para startup.sh

**Executado**

- Enviado durante a execução do 003. `scripts/up.sh` renomeado para `scripts/startup.sh` (`git mv`, mantendo o bit de execução) na branch da PR #3.
- Referências atualizadas em `.ai/tech-stack.md`, `.ai/standards.md`, `.env.example`, `compose.yaml`, no comentário do próprio script e na descrição da PR #3.
- Verificação: `scripts/startup.sh` sobe tudo e `/health` responde 200.
- Commit `8c1e600` e push. A branch do contrato (003) foi recriada em cima desse commit.
