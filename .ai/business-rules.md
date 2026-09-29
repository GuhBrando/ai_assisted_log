# Regras de negócio

> Fonte: `docs/log_api_system_documentation.pdf` (API de Logs — Documento do Sistema, 22/09/2026).
> Como o sistema implementa estas regras: [architecture.md](architecture.md) · Padrões de código: [standards.md](standards.md).

## Domínio

A API de Logs recebe os logs enviados pelas aplicações de qualquer cliente e os guarda isolados por cliente. Cada log informa uma mensagem, um nível, um `correlationId` opcional (liga os logs de um mesmo fluxo) e um `informationData` opcional (o objeto que a aplicação estava manipulando).

Escopo desta versão: ingestão de logs, cadastro de clientes, aplicações e usuários, retenção automática por cliente, painel de consulta de logs e alertas.

### Entidades

| Entidade | O que representa |
|---|---|
| `Customer` | Empresa cliente da plataforma; define o prazo de retenção dos seus logs |
| `User` | Pessoa que acessa a plataforma de logs; pertence a um cliente. Não é o usuário final do sistema do cliente |
| `Application` | Sistema do cliente que envia logs; substitui o antigo campo livre `ApplicationName` |
| `ApiKey` | Credencial de uma aplicação; guardada só como hash, pode expirar ou ser revogada |
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
| `Application` | `id: ObjectId`, `customer_id: ObjectId`, `name: str`, `api_keys: list[ApiKey]`, `created_at: datetime` |
| `ApiKey` | `key_hash: str`, `prefix: str`, `expires_at?: datetime`, `revoked_at?: datetime`; método `is_valid(now) -> bool` |
| `LogCreate` | `correlation_id?: UUID`, `level: LogLevel`, `message: str`, `exception?: str`, `environment: str`, `information_data?: dict`, `occurred_at: datetime` |
| `LogDocument` | Tudo de `LogCreate` + `id: ObjectId`, `customer_id: ObjectId`, `application_id: ObjectId`, `application_name: str`, `received_at: datetime`, `expire_at: datetime` |

### Relacionamentos

| De | Para | Cardinalidade | Observação |
|---|---|---|---|
| `Customer` | `User` | 1 → 0..* | Por `customer_id` |
| `Customer` | `Application` | 1 → 0..* | Por `customer_id` |
| `Application` | `ApiKey` | 1 → 1..* | Embutidas na aplicação |
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

O cliente e a aplicação donos de um log são definidos só pela API key do cabeçalho `X-API-Key`. Nenhum campo do corpo troca o cliente ou a aplicação: um corpo com `customer_id` é recusado com 422 e nada é gravado.

### RN-02 — Validade da API key

A chave precisa existir e não pode estar expirada nem revogada (`is_valid(now)`). Ela é inválida quando `expires_at` ou `revoked_at` está no passado. Chave ausente, inexistente, expirada ou revogada → 401.

### RN-03 — Cliente ativo

Uma chave válida de um cliente com `is_active = false` → 403.

### RN-04 — Validação do corpo

O corpo é validado como `LogCreate`. São obrigatórios `level`, `message`, `environment` e `occurred_at`. `level` só aceita os valores de `LogLevel` (ex.: `level: 9` → 422). Campo inválido ou extra → 422.

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
| `customer_id` | Cliente dono da API key |
| `application_id` | Aplicação dona da API key |
| `application_name` | Cópia de `Application.name` |
| `received_at` | Horário em que o log chegou |
| `expire_at` | Ver RN-08 |

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

### RN-13 — Aplicação cadastrada

A aplicação que envia logs é uma entidade cadastrada (`Application`), não um texto livre. O nome dela é copiado em cada log. Isso evita que "Checkout" e "checkout" virem aplicações diferentes.

### RN-14 — Filtro por nível

Filtrar "a partir de" um nível é comparar o valor numérico: "a partir de Warning" é `level >= 3`.

## Códigos de resposta

Respostas de `POST /logs`:

| Código | Quando acontece |
|---|---|
| 201 Created | Log gravado; o corpo traz o id |
| 401 Unauthorized | API key ausente, inexistente, expirada ou revogada |
| 403 Forbidden | O cliente dono da chave está inativo |
| 413 Payload Too Large | `information_data` acima do limite de tamanho |
| 422 Unprocessable Entity | Corpo inválido, campo extra (como `customer_id`) ou chave com `$` ou `.` em `information_data` |

Ordem das checagens: API key (401) → cliente ativo (403) → corpo (422) → tamanho e chaves de `information_data` (413 ou 422) → gravação (201).

## Casos de aceitação

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Log válido | Chave válida, corpo completo | 201; documento com `customerId`, `applicationName`, `receivedAt` e `expireAt` preenchidos pela API |
| Sem API key | Cabeçalho ausente | 401 |
| Chave revogada ou expirada | `revokedAt` ou `expiresAt` no passado | 401 |
| Cliente inativo | Chave válida de cliente com `isActive: false` | 403 |
| Tentativa de trocar o dono | Corpo com `customer_id` | 422 e nada gravado |
| Nível inválido | `level: 9` | 422 |
| Payload grande | `information_data` acima do limite | 413 |
| Chave proibida | `information_data` com chave `$where` ou `a.b` | 422 |
| Mascaramento | `information_data` com `password` e `cpf` | 201; valores mascarados no banco |
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

- [ ] Convenção de nomes do JSON da API: o documento cita `correlationId`/`informationData` na visão geral e `customer_id` nos exemplos de payload.
- [ ] Algoritmo de hash das API keys. Precisa ser determinístico para a busca pelo índice `apiKeys.keyHash`.
- [ ] Regras do painel de consulta de logs e dos alertas: estão no escopo, mas o documento ainda não as detalha.
