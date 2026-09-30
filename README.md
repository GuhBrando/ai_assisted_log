# API de Logs

API para ingestão e consulta de logs, com contrato OpenAPI em [`docs/api/openapi.yaml`](docs/api/openapi.yaml). O backend Python usa FastAPI e MongoDB; o cliente desktop está em [`frontend/`](frontend/).

## Backend local

O ambiente com API, MongoDB e Swagger UI sobe com Docker Compose:

```bash
scripts/startup.sh
```

A API fica em `http://127.0.0.1:8000` e o Swagger do contrato em `http://127.0.0.1:8080`. Consulte [Tech Stack](.ai/tech-stack.md), [arquitetura](.ai/architecture.md) e [guia do contrato](docs/api/README.md) para detalhes. Atualmente, no backend, apenas `GET /health` está implementado; as rotas de painel usadas pelo frontend são propostas no OpenAPI.

## Frontend desktop (Windows)

Requer Node.js 22 e npm. Em dois terminais, a partir de `frontend/`:

```bash
npm ci
npm run mock   # Prism em http://127.0.0.1:4010
```

```bash
npm start      # Electron em desenvolvimento; usa somente o Prism local
```

O login de desenvolvimento pode usar `ana@example.com` e `uma-senha-longa`, exemplos do contrato. O Prism responde com dados de exemplo; não persiste mudanças e pode repetir a mesma página mesmo quando retorna `next_cursor`. O frontend **empacotado** usa exclusivamente a API local em `http://127.0.0.1:8000`.

Comandos adicionais em `frontend/`:

```bash
npm run generate:api  # regenera src/api/schema.d.ts do OpenAPI
npm run typecheck
npm run lint
npm test
npm run package       # aplicativo Windows em out/
npm run make          # instalador Windows em out/make/
```

A tela oferece filtros por aplicação, nível mínimo, período, correlation ID e tags, além de busca textual **somente na página carregada**. Contagens e gráfico usam apenas os registros dessa página. A paginação usa o `next_cursor` opaco. Detalhes e stack trace vêm de `GET /logs/{log_id}`. A sessão termina ao fechar o aplicativo ou ao receber 401; o token fica apenas na memória do processo principal do Electron.

Busca global, agregações completas e tempo real aguardam contratos de backend próprios. O backend ainda precisa implementar e validar `POST /auth/login`, `GET /logs`, `GET /logs/{log_id}` e `GET /applications` antes de testes de integração reais. O instalador Windows gerado nesta etapa não é assinado digitalmente.
