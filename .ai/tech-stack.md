# Tech stack

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complemento posterior ao documento: PyJWT, para o token de acesso temporário.
> Padrões de código: [standards.md](standards.md) · Decisões de arquitetura: [architecture.md](architecture.md).

Só as tecnologias abaixo estão aprovadas. Adicionar uma biblioteca nova exige registrá-la aqui, e em [architecture.md](architecture.md) se ela mudar uma decisão.

## Stack aprovada

| Camada | Tecnologia | Versão | Papel |
|---|---|---|---|
| Linguagem | Python | a definir | — |
| API | FastAPI | a definir | Rotas, injeção de dependências, autenticação (`X-API-Key` e Bearer), Swagger |
| Validação | Pydantic | **v2** | Modelos de entrada, documento e resposta; rejeita campos extras |
| Validação de e-mail | email-validator (extra `pydantic[email]`) | a definir | Exigido pelo `EmailStr` do `User` |
| Acesso a dados | PyMongo Async (`AsyncMongoClient`) | ≥ 4.13 (API assíncrona estável) | Driver oficial do MongoDB |
| Banco | MongoDB | a definir | Documentos BSON, índices e TTL para retenção |
| Senhas | pwdlib + Argon2 (`pwdlib[argon2]`) | a definir | Hash das senhas dos usuários da plataforma |
| Tokens de acesso | PyJWT | a definir | Emitir e validar o JWT de 1 hora das aplicações (HS256) |
| Testes | pytest, httpx, Testcontainers (MongoDB) | a definir | Testes de endpoint contra um MongoDB real em Docker |

O documento do sistema só fixa a versão do Pydantic (v2). A versão mínima do PyMongo é a primeira em que a API assíncrona saiu do beta. As demais versões devem ser fixadas no gerenciador de dependências quando o projeto for criado, e esta tabela atualizada.

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
| Segredo de assinatura | Variável de ambiente `JWT_SECRET`, com pelo menos 32 bytes aleatórios |
| Algoritmo | `HS256` |
| Validade | 3600 segundos (1 hora), limitada à expiração da API key |
| Claims obrigatórias | `sub` (id da aplicação), `iat`, `exp`, `jti` |

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

## A definir

- Versões de Python, FastAPI, MongoDB, pwdlib, PyJWT, pytest, httpx e Testcontainers.
- Plugin de testes assíncronos do pytest (ex.: pytest-asyncio ou o plugin do anyio).
- Algoritmo de hash das API keys (ver [ADR-008](architecture.md#adr-008--api-keys-guardadas-como-hash--prefixo)).
