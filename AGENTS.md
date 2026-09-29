# AGENTS.md

Orientações para agentes de IA (LLMs) que trabalham neste repositório.

## Contexto do projeto

Antes de mudar código ou documentação, ler os arquivos de contexto em `.ai/`:

| Arquivo | Conteúdo |
|---|---|
| [.ai/business-rules.md](.ai/business-rules.md) | Domínio, regras de negócio, códigos de resposta e pontos em aberto |
| [.ai/architecture.md](.ai/architecture.md) | Componentes, fluxos, persistência e decisões (ADRs) |
| [.ai/standards.md](.ai/standards.md) | Padrões de código |
| [.ai/tech-stack.md](.ai/tech-stack.md) | Stack aprovada, versões e o que não usar |
| [.ai/prompts.md](.ai/prompts.md) | Registro dos prompts enviados a LLMs e do que foi executado |

## Registro de prompts

Todo prompt enviado a uma LLM para trabalhar neste repositório é registrado em [.ai/prompts.md](.ai/prompts.md), junto com tudo o que foi executado. Assim, qualquer mudança pode ser rastreada até o pedido que a originou.

- **Todo prompt entra:** inclusive perguntas sem mudança de arquivo, correções no meio de uma tarefa e prompts interrompidos.
- **Quem registra** é a própria LLM que recebeu o prompt, ao terminar de executá-lo.
- **Prompt na íntegra,** como foi escrito. Não resumir nem corrigir.
- **Só acrescentar:** uma entrada nova no fim do arquivo, com o número seguinte. Não reescrever nem apagar entradas antigas; uma correção vira uma entrada nova.
- **Mesmo commit:** a entrada vai no mesmo commit (ou PR) das mudanças que o prompt gerou. Prompt sem mudança de arquivo entra no próximo commit.
- **Sem segredos nem dados pessoais:** API keys, tokens, senhas, o conteúdo do `.env` e dados pessoais viram `[removido]`, tanto no prompt quanto no que foi executado.

### Formato da entrada

```markdown
## NNN — Título curto do pedido

- **Data:** AAAA-MM-DD
- **Branch:** `nome-da-branch` (uma ou mais)
- **PR:** #N (ou —)

**Prompt**

> Texto do prompt na íntegra.

**Executado**

- Arquivos criados, alterados ou removidos, e o que mudou em cada um.
- Comandos que mudaram algum estado (build, commit, push, PR) e as verificações feitas, com o resultado.
- Decisões tomadas e o que ficou em aberto.
```
