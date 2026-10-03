# API de Logs

API para ingestão e consulta de logs, com contrato OpenAPI em [`docs/api/openapi.yaml`](docs/api/openapi.yaml). O backend Python usa FastAPI e MongoDB; o cliente desktop está em [`frontend/`](frontend/).

## Backend local

O ambiente com API, MongoDB e Swagger UI sobe com Docker Compose:

```bash
scripts/startup.sh
```

A API fica em `http://127.0.0.1:8000` e o Swagger do contrato em `http://127.0.0.1:8080`. Consulte [Tech Stack](.ai/tech-stack.md), [arquitetura](.ai/architecture.md) e [guia do contrato](docs/api/README.md) para detalhes. As rotas usadas pelo frontend (`POST /auth/login`, `GET /logs`, `GET /logs/{log_id}` e `GET /applications`) já estão implementadas.

## Frontend desktop (Windows)

Requer Node.js 22 e npm. Com o backend no ar (`scripts/startup.sh`), a partir de `frontend/`:

```bash
npm ci
npm start      # Electron em desenvolvimento, ligado à API local em http://127.0.0.1:8000
```

O login usa um usuário da plataforma. Num banco vazio, crie o cliente e o primeiro usuário com `POST /customers` no Swagger da API (`http://127.0.0.1:8000/docs`). Os logs chegam pelas aplicações do cliente: `POST /applications`, `POST /applications/{id}/api-keys`, `POST /auth/token` com a chave e `POST /logs` com o token.

Para desenvolver sem backend, use o mock em dois terminais:

```bash
npm run mock         # Prism em http://127.0.0.1:4010
```

```bash
npm run start:mock   # Electron apontando para o Prism
```

No mock, o login pode usar `ana@example.com` e `uma-senha-longa`, exemplos do contrato. O Prism na porta 4010 valida as respostas contra o OpenAPI e encaminha para uma massa determinística local de 1.600 logs (porta interna 4011). A massa cobre fluxos correlacionados, erros, retries, tags, períodos vazios e páginas sucessivas; não usa MongoDB nem persiste mudanças. A tela mostra se está ligada à API local ou ao mock. O frontend **empacotado** usa exclusivamente a API local em `http://127.0.0.1:8000`.

Comandos adicionais em `frontend/`:

```bash
npm run generate:api  # regenera src/api/schema.d.ts do OpenAPI
npm run typecheck
npm run lint
npm test
npm run verify:mock   # com npm run mock ativo: paginação e filtros via Prism
npm run package       # aplicativo Windows em out/
npm run make          # instalador Windows em out/make/
```

A tela oferece filtros por aplicação, nível mínimo, período, correlation ID e tags, além de busca textual **somente na página carregada**. Os filtros de período e os timestamps exibem `DD/MM/YYYY HH:MM:SS` no fuso local; a requisição usa ISO 8601 com fuso, conforme o contrato. Início é inclusivo e Fim é exclusivo. Tags sugeridas vêm apenas da página carregada. Contagens e gráfico usam apenas os registros dessa página. A paginação usa o `next_cursor` opaco e confirma que a próxima página contém registros antes de habilitar a navegação; consulta somente a página atual e a próxima. Detalhes e stack trace vêm de `GET /logs/{log_id}`. A sessão termina ao fechar o aplicativo ou ao receber 401; o token fica apenas na memória do processo principal do Electron.

Busca global, agregações completas e tempo real aguardam contratos de backend próprios. O instalador Windows gerado nesta etapa não é assinado digitalmente.
