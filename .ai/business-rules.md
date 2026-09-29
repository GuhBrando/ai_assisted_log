# Regras de negócio

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Complementos posteriores ao documento: tags (RN-15) e token de acesso temporário (RN-16).
> Como o sistema implementa estas regras: [architecture.md](architecture.md) · Padrões de código: [standards.md](standards.md).

## Domínio

A API de Logs recebe os logs enviados pelas aplicações de qualquer cliente e os guarda isolados por cliente. Cada log informa uma mensagem, um nível, um `correlationId` opcional (liga os logs de um mesmo fluxo), um `informationData` opcional (o objeto que a aplicação estava manipulando) e tags opcionais para filtro.

A aplicação troca a sua API key por um token de acesso válido por 1 hora e usa esse token para enviar logs.

Escopo desta versão: ingestão de logs, cadastro de clientes, aplicações e usuários, retenção automática por cliente, painel de consulta de logs e alertas. Complementos: tags em aplicações e logs, token de acesso de 1 hora.

### Entidades

| Entidade | O que representa |
|---|---|
| `Customer` | Empresa cliente da plataforma; define o prazo de retenção dos seus logs |
| `User` | Pessoa que acessa a plataforma de logs; pertence a um cliente. Não é o usuário final do sistema do cliente |
| `Application` | Sistema do cliente que envia logs; substitui o antigo campo livre `ApplicationName` |
| `ApiKey` | Credencial de longa duração de uma aplicação; guardada só como hash, pode expirar ou ser revogada. Serve só para obter tokens de acesso |
| `AccessToken` | Credencial temporária (1 hora) que a aplicação obtém com a API key e usa para enviar logs. Não é gravado no banco |
| `LogCreate` | O log como o cliente envia |
| `LogDocument` | O log como a API grava; estende `LogCreate` com os campos que só a API preenche |
| `LogRead` | O log nas respostas, com `id` como texto |
| `LogLevel` | Enum numérico de severidade |

### Atributos

Campos com `?` são opcionais.

| Entidade | Campos |
|---|---|
| `Customer` | `id: ObjectId`, `name: str`, `is_active: bool`, `retention_days: int`, `created_at: datetime` |
| `User` | `id: ObjectId`, `customer_id: ObjectId`, `name: str`, `email: EmailStr`, `password_hash: str`, `created_at: datetime` |
| `Application` | `id: ObjectId`, `customer_id: ObjectId`, `name: str`, `api_keys: list[ApiKey]`, `tags: list[str]`, `created_at: datetime` |
| `ApiKey` | `key_hash: str`, `prefix: str`, `expires_at?: datetime`, `revoked_at?: datetime`; método `is_valid(now) -> bool` |
| `AccessToken` | `sub` (id da aplicação), `iat` (emitido em), `exp` (expira em), `jti` (id único do token) |
| `LogCreate` | `correlation_id?: UUID`, `level: LogLevel`, `message: str`, `exception?: str`, `environment: str`, `information_data?: dict`, `tags?: list[str]` (padrão: lista vazia), `occurred_at: datetime` |
| `LogDocument` | Tudo de `LogCreate` + `id: ObjectId`, `customer_id: ObjectId`, `application_id: ObjectId`, `application_name: str`, `received_at: datetime`, `expire_at: datetime`. Em `tags` fica a lista final (RN-15) |

### Relacionamentos

| De | Para | Cardinalidade | Observação |
|---|---|---|---|
| `Customer` | `User` | 1 → 0..* | Por `customer_id` |
| `Customer` | `Application` | 1 → 0..* | Por `customer_id` |
| `Application` | `ApiKey` | 1 → 1..* | Embutidas na aplicação |
| `Application` | `AccessToken` | 1 → 0..* | Emitidos com uma API key; não são gravados |
| `Application` | `LogDocument` | 1 → 0..* | Por `application_id` |
| `Customer` | `LogDocument` | 1 → 0..* | `customer_id` desnormalizado no log |

### LogLevel

| Valor | Nome |
|---|---|
| 0 | `TRACE` |
| 1 | `DEBUG` |
| 2 | `INFORMATION` |
| 3 | `WARNING` |
| 4 | `ERROR` |
| 5 | `CRITICAL` |

### Datas do log

- `occurred_at`: quando o evento aconteceu no cliente. Enviada pelo cliente.
- `received_at`: quando o log chegou à API. Preenchida pela API.

## Regras

### RN-01 — Dono do log

O cliente e a aplicação donos de um log são definidos só pela credencial da aplicação: o token de acesso (RN-16), que é emitido a partir da API key. Nenhum campo do corpo troca o cliente ou a aplicação: um corpo com `customer_id` é recusado com 422 e nada é gravado.

### RN-02 — Validade da API key

Checada na emissão do token (`POST /auth/token`). A chave precisa existir e não pode estar expirada nem revogada (`is_valid(now)`). Ela é inválida quando `expires_at` ou `revoked_at` está no passado. Chave ausente, inexistente, expirada ou revogada → 401.

### RN-03 — Cliente ativo

Checado na emissão do token e em cada envio de log. Cliente com `is_active = false` → 403, mesmo que o token ainda não tenha expirado.

### RN-04 — Validação do corpo

O corpo é validado como `LogCreate`. São obrigatórios `level`, `message`, `environment` e `occurred_at`. `level` só aceita os valores de `LogLevel` (ex.: `level: 9` → 422). Campo inválido ou extra, ou tag fora das regras de RN-15 → 422.

### RN-05 — Limites de `information_data`

- É opcional e livre (documento BSON).
- Tem limite de tamanho: acima dele → 413. O valor está em aberto (sugestão: 64 KB).
- Chaves com `$` ou `.` são recusadas (ex.: `$where`, `a.b`) → 422.

### RN-06 — Mascaramento de dados sensíveis

Como o cliente pode enviar o request inteiro em `information_data`, a API mascara campos sensíveis, como senha (`password`), CPF (`cpf`) e cartão, antes de gravar. O log é aceito (201) e o banco guarda só os valores mascarados. A lista final de campos está em aberto.

### RN-07 — Campos preenchidos pela API

A API preenche, e o cliente nunca envia:

| Campo | Origem |
|---|---|
| `id` | `ObjectId` gerado na inserção |
| `customer_id` | Cliente dono da aplicação do token |
| `application_id` | Aplicação do token (`sub`) |
| `application_name` | Cópia de `Application.name` |
| `received_at` | Horário em que o log chegou |
| `expire_at` | Ver RN-08 |
| `tags` (lista final) | Tags da aplicação somadas às do log (RN-15) |

### RN-08 — Retenção por cliente

Ao gravar, `expire_at = received_at + customer.retention_days`. Depois dessa data o log é apagado automaticamente. Exemplo: cliente com `retention_days = 7` → `expire_at = received_at + 7 dias`. A retenção limitada atende ao princípio de necessidade da LGPD.

### RN-09 — Isolamento por cliente

Toda consulta de logs filtra pelo cliente. Um usuário do cliente A nunca vê logs do cliente B; cada usuário vê só os logs do cliente ao qual pertence (`User.customer_id`).

### RN-10 — Imutabilidade

Logs só são inseridos. Não existe endpoint de alteração; um log sai do sistema só pela retenção (RN-08).

### RN-11 — Usuários

- Todo usuário pertence a um cliente.
- O e-mail é único: um segundo cadastro com o mesmo e-mail é recusado.
- A senha é guardada só como hash (pwdlib + Argon2), nunca em texto.

### RN-12 — API keys

- São geradas pela plataforma e mostradas uma única vez.
- O banco guarda só o hash e um prefixo curto (ex.: `lx_ab12`) para identificação.
- Uma aplicação pode ter várias chaves; cada uma expira ou é revogada sem afetar as outras.
- Servem só para obter tokens de acesso (RN-16); não são aceitas no envio de logs.

### RN-13 — Aplicação cadastrada

A aplicação que envia logs é uma entidade cadastrada (`Application`), não um texto livre. O nome dela é copiado em cada log. Isso evita que "Checkout" e "checkout" virem aplicações diferentes.

### RN-14 — Filtro por nível

Filtrar "a partir de" um nível é comparar o valor numérico: "a partir de Warning" é `level >= 3`.

### RN-15 — Tags

Tags são uma dimensão extra de filtro, no formato `chave:valor` (ex.: `team:payments`, `feature:pix`, `region:sa-east-1`).

- **Onde existem:**
  - **Aplicação:** definidas no cadastro; valem para todos os logs da aplicação (ex.: `team:checkout`).
  - **Log:** enviadas opcionalmente em cada log; descrevem aquele evento (ex.: `feature:pix`).
- **Formato:** `chave:valor`, separados pelo primeiro `:`. A chave usa letras minúsculas, dígitos, `_` e `-`; o valor não pode ser vazio nem ter espaços. Fora do formato → 422.
- **Normalização:** antes de validar, a API remove os espaços das pontas e converte para minúsculas; depois descarta as repetidas. `" Feature:PIX"` vira `feature:pix`. É o mesmo cuidado de "Checkout" e "checkout" (RN-13).
- **Limites:** até 20 tags por log e por aplicação, com até 100 caracteres cada (sugestão, ver [Pontos em aberto](#pontos-em-aberto)). Acima disso → 422.
- **Tags gravadas no log:** as da aplicação somadas às do log. Tags do log com uma chave que a aplicação já define são descartadas: vale a da aplicação, e o cliente não consegue trocar pelo log uma tag definida no cadastro.
- **Cópia na ingestão:** mudar as tags de uma aplicação não altera os logs já gravados.
- **Filtro:** filtrar por várias tags retorna os logs que têm todas elas (E). O filtro por tags sempre vem junto com o filtro por cliente (RN-09).
- **Sem duplicar campos:** não usar tags para o que já tem campo próprio (`level`, `environment`, aplicação, `correlation_id`).
- **Sem dados pessoais:** tags não passam pelo mascaramento (RN-06) e ficam indexadas. Não podem conter CPF, e-mail, nome de pessoa nem outro dado pessoal.

### RN-16 — Token de acesso temporário

- A aplicação obtém o token em `POST /auth/token`, enviando a API key no cabeçalho `X-API-Key`. A emissão exige chave válida (RN-02) e cliente ativo (RN-03).
- O token vale por **1 hora**. Se a API key expirar antes, o token expira junto: `exp = min(emitido_em + 1 hora, api_key.expires_at)`.
- `POST /logs` aceita só o token, no cabeçalho `Authorization: Bearer <token>`. A API key não é aceita no envio de logs.
- Token ausente, inválido ou expirado → 401.
- Não existe renovação: perto de expirar, a aplicação pede outro token com a API key. Uma aplicação pode ter vários tokens válidos ao mesmo tempo (ex.: um por instância).
- O token não é gravado no banco. Revogar uma API key impede novos tokens na hora, mas os já emitidos com ela continuam válidos até expirar (no máximo 1 hora).
- Desativar o cliente bloqueia os envios na hora (RN-03), mesmo com token válido.

## Códigos de resposta

### `POST /auth/token`

| Código | Quando acontece |
|---|---|
| 200 OK | Token emitido; o corpo traz `access_token`, `token_type` (`bearer`) e `expires_in` (segundos) |
| 401 Unauthorized | API key ausente, inexistente, expirada ou revogada |
| 403 Forbidden | O cliente dono da chave está inativo |

### `POST /logs`

| Código | Quando acontece |
|---|---|
| 201 Created | Log gravado; o corpo traz o id |
| 401 Unauthorized | Token ausente, inválido ou expirado (inclui envio só com `X-API-Key`) |
| 403 Forbidden | O cliente dono da aplicação está inativo |
| 413 Payload Too Large | `information_data` acima do limite de tamanho |
| 422 Unprocessable Entity | Corpo inválido, campo extra (como `customer_id`), tag fora do formato ou acima do limite, ou chave com `$` ou `.` em `information_data` |

Ordem das checagens em `POST /logs`: token (401) → cliente ativo (403) → corpo e tags (422) → tamanho e chaves de `information_data` (413 ou 422) → gravação (201).

Códigos dos demais endpoints e formato do corpo de erro: [`docs/api/openapi.yaml`](../docs/api/openapi.yaml).

## Casos de aceitação

### Token de acesso

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Token emitido | `POST /auth/token` com chave válida | 200; `token_type: bearer`, `expires_in: 3600` |
| Sem API key | `POST /auth/token` sem o cabeçalho | 401 |
| Chave revogada ou expirada | `POST /auth/token` com `revokedAt` ou `expiresAt` no passado | 401 |
| Chave perto de expirar | Chave com `expiresAt` daqui a 10 minutos | 200; `expires_in` ≤ 600 |
| Cliente inativo na emissão | Chave válida de cliente com `isActive: false` | 403 |

### Envio de logs

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Log válido | Token válido, corpo completo | 201; documento com `customerId`, `applicationName`, `tags`, `receivedAt` e `expireAt` preenchidos pela API |
| Sem token | `POST /logs` sem `Authorization` | 401 |
| API key no lugar do token | `POST /logs` só com `X-API-Key` | 401 |
| Token expirado | Token com `exp` no passado | 401 |
| Token adulterado | Token com assinatura inválida | 401 |
| Cliente desativado com token válido | Token emitido antes de `isActive` virar `false` | 403 |
| Tentativa de trocar o dono | Corpo com `customer_id` | 422 e nada gravado |
| Nível inválido | `level: 9` | 422 |
| Payload grande | `information_data` acima do limite | 413 |
| Chave proibida | `information_data` com chave `$where` ou `a.b` | 422 |
| Mascaramento | `information_data` com `password` e `cpf` | 201; valores mascarados no banco |

### Tags

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Normalização | `tags: [" Feature:PIX", "feature:pix"]` | 201; gravado só `feature:pix` |
| Tag fora do formato | `tags: ["pix"]` | 422 |
| Excesso de tags | 21 tags no log | 422 |
| Tags da aplicação | Aplicação com `team:checkout`, log com `feature:pix` | Log gravado com as duas |
| Precedência da aplicação | Aplicação com `team:checkout`, log com `team:outro` | Log gravado só com `team:checkout` |
| Filtro por tags | Filtro `team:checkout` e `feature:pix` | Só logs com as duas tags, e só do cliente do usuário |

### Retenção, isolamento e usuários

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Retenção | Cliente com `retentionDays: 7` | `expireAt = receivedAt + 7 dias` |
| Isolamento | Consulta com usuário do cliente A | Nenhum log do cliente B aparece |
| E-mail duplicado | Dois usuários com o mesmo e-mail | Segundo cadastro recusado |

## Pontos em aberto

Do documento do sistema:

- [ ] Um usuário pode atender mais de um cliente? Se sim, `customerId` vira `customerIds`.
- [ ] Qual o limite de tamanho de `information_data`? Sugestão: 64 KB.
- [ ] Quais campos entram na lista de mascaramento, e ela é configurável por cliente?
- [ ] A API aceita envio em lote (`POST /logs/batch`) nesta versão?

Levantados ao separar o documento nestes arquivos:

- [x] Convenção de nomes do JSON da API: `snake_case` ([ADR-018](architecture.md#adr-018--json-da-api-em-snake_case)).
- [ ] Algoritmo de hash das API keys. Precisa ser determinístico para a busca pelo índice `apiKeys.keyHash`.
- [ ] Regras do painel de consulta de logs e dos alertas: estão no escopo, mas o documento ainda não as detalha.

Dos complementos (tags e token):

- [ ] Limites de tags: até 20 por log e por aplicação, com até 100 caracteres cada?
- [ ] Revogar uma API key deve derrubar na hora os tokens já emitidos com ela? Hoje eles valem até expirar (no máximo 1 hora); derrubar na hora exigiria guardar os tokens ou uma lista de revogados.

Propostas do [contrato da API](../docs/api/openapi.yaml), a validar:

- [ ] Login de usuários: `POST /auth/login` com e-mail e senha devolve um token de usuário de 1 hora, nas mesmas regras do token de aplicação. Como diferenciar os dois tokens (sugestão: claim `aud`)?
- [ ] Usuário de cliente inativo: o contrato propõe 403 no login e em todas as rotas do painel, como na ingestão (RN-03).
- [ ] Quem cadastra clientes? O contrato propõe auto-cadastro sem credencial (`POST /customers`, com o primeiro usuário). E quem ativa ou desativa um cliente (`is_active`)? Hoje nenhuma rota altera esse campo.
- [ ] Nome de aplicação único dentro do cliente, sem diferenciar maiúsculas de minúsculas (409), com índice único `{ customerId: 1, name: 1 }`.
- [ ] Prefixo da API key único dentro da aplicação, porque identifica a chave na revogação.
- [ ] Política de senha: o contrato propõe de 8 a 128 caracteres.
- [ ] Paginação de `GET /logs` por cursor, com até 100 logs por página (padrão 50).
- [ ] Formato do valor mascarado em `information_data` (os exemplos usam `***`).
