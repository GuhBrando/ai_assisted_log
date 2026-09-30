# Planejamento inicial do frontend desktop

## 1. Stack recomendada para o frontend

**Electron + React + TypeScript**, com Electron Forge e seu template TypeScript/Webpack, npm e `package-lock.json`. O template oferece empacotamento e suporte a React; o plugin Vite do Forge ainda é classificado como experimental.

Usar TanStack Query para requisições e cache, e `openapi-typescript` para gerar tipos a partir do contrato existente.

[Electron Forge](https://www.electronforge.io/templates/typescript-%2B-webpack-template) · [Integração com React](https://www.electronforge.io/guides/framework-integration/react-with-typescript)

---

## 2. Arquitetura sugerida

- Criar `frontend/` com três áreas: **processo principal** do Electron para chamadas à API, **preload** com uma interface IPC pequena e tipada, e **renderer** React para telas, componentes e estado visual. O token de usuário fica apenas na memória do processo principal. A API inicial é fixa em `http://127.0.0.1:8000`.

- Organizar o renderer em login, tela de logs, filtros, lista e painel de detalhes. A tela principal mostra nível com texto e cor, horário, aplicação, mensagem, tags e trecho da exceção. O detalhe exibe os campos completos, `information_data` recolhível e `exception` como texto pré-formatado para preservar o stack trace.

- Usar os endpoints propostos `POST /auth/login`, `GET /logs`, `GET /logs/{log_id}` e `GET /applications`. Os filtros seguem o contrato: aplicação, nível mínimo, período, `correlation_id` e tags combinadas com **E**. Clicar em um `correlation_id` aplica esse filtro; o `id` abre o detalhe e pode ser copiado.

- A busca textual inicial examina **somente a página carregada**, com esse alcance indicado claramente na interface.

- Para grandes volumes, usar páginas de até 100 registros, `next_cursor` e navegação de volta por um histórico local de cursores. Contagens por severidade e destaques visuais representam apenas os registros da página atual.

- Uma futura atualização periódica pode consultar a primeira página e deduplicar por `id`; tempo real por push dependerá de contrato próprio.

[Contrato atual](../../docs/api/openapi.yaml)

### Identidade visual e experiência

A interface deve seguir uma identidade **clean, técnica e focada em observabilidade**, priorizando a leitura rápida dos logs e a identificação de problemas.

Usar inicialmente um **tema escuro**, com:

- poucos elementos decorativos;
- contraste suficiente entre fundo, painéis e conteúdo;
- cores de severidade consistentes;
- tipografia de alta legibilidade;
- fonte monoespaçada para logs, IDs e stack traces;
- espaçamento compacto, evitando transformar a aplicação em um dashboard com excesso de cards.

As cores não devem ser a única forma de identificar severidade: manter também o nome do nível (`INFO`, `WARN`, `ERROR`, etc.).

A tela principal pode ser dividida visualmente em:

1. filtros e seleção do período;
2. visão resumida do período/página;
3. lista principal de logs;
4. painel de detalhes do registro selecionado.

### Filtro de data e hora

O filtro de período deve permitir selecionar:

- data e hora inicial;
- data e hora final.

O frontend deve validar pelo menos:

- data/hora inicial válida;
- data/hora final válida;
- data final não anterior à inicial.

A validação deve acontecer antes de realizar a consulta e apresentar o erro próximo ao próprio filtro.

Podem ser incluídos atalhos de período, como **última hora**, **últimas 24 horas** e **hoje**, desde que não acrescentem complexidade relevante.

Se o backend já fornecer, ou puder fornecer de maneira simples, a menor data existente nos logs, ela pode ser utilizada como limite mínimo do seletor de data, impedindo consultas anteriores ao período existente no banco.

Caso essa informação não esteja disponível no contrato atual, não criar um novo contrato apenas para esta primeira etapa. Registrar a possibilidade como evolução futura.

### Visualização de chamadas e volume

Adicionar uma área visual compacta acima da lista para facilitar a percepção do comportamento dos logs.

O principal elemento pode ser um **gráfico temporal simples**, mostrando a quantidade de registros/chamadas ao longo do período selecionado.

Também podem existir indicadores pequenos para severidades, como:

- total;
- INFO;
- WARN;
- ERROR.

Nesta primeira versão, esses indicadores e o gráfico devem trabalhar apenas com os dados realmente disponíveis no frontend.

Como o contrato atual não oferece totais agregados, quando forem calculados a partir da página carregada isso deve ficar claro para o usuário.

Não adicionar gráficos que não contribuam diretamente para investigação ou leitura dos logs.

### Lista e investigação

A lista deve permanecer como principal área da aplicação.

Priorizar visualmente:

- horário;
- nível;
- aplicação;
- mensagem;
- tags;
- indicação de exceção.

Erros e warnings devem ser facilmente identificáveis sem tornar a tela excessivamente colorida.

Ao selecionar um registro, o painel de detalhes deve permitir visualizar os campos completos, `information_data`, `exception` e identificadores disponíveis.

O `correlation_id`, quando existente, deve continuar sendo um elemento importante para investigação e permitir aplicar o filtro correspondente rapidamente.

---

## 3. Ordem de implementação

1. **Base desktop:** criar `frontend/`, configuração Forge/Webpack, janela, preload, scripts de desenvolvimento e pacote Windows. Validar que o renderer não tem acesso direto a Node e que a janela abre no modo de desenvolvimento e empacotada.

2. **Contrato e comunicação:** gerar tipos do OpenAPI; implementar no processo principal cliente HTTP, login, logout, erros e métodos IPC restritos. Usar os exemplos do contrato como dados de desenvolvimento até os endpoints existirem.

3. **Base visual e tela principal:** definir a identidade visual inicial, estrutura de layout, filtros, seleção de data/hora, estados de carregamento/erro/vazio, lista paginada, indicadores de severidade e resumo da página.

4. **Visualização temporal:** adicionar o gráfico simples de volume de registros utilizando apenas os dados disponíveis nessa etapa, mantendo claro quando as informações representam somente a página carregada.

5. **Investigação:** adicionar filtros, busca na página, detalhe, stack trace e navegação por `correlation_id`. Testar combinações de filtros, período, validações de data/hora, troca de página e ausência de campos opcionais.

6. **Integração e entrega:** executar testes de componentes e do cliente, testar com a API quando as rotas estiverem disponíveis e validar o pacote Windows. Criar `README.md` com instalação, Docker/API e comandos do frontend; atualizar `.ai/tech-stack.md` e a arquitetura para registrar as decisões. Registrar os prompts pendentes em `.ai/prompts.md` no commit das alterações e fazer a revisão final exigida pelo `AGENTS.md`.

---

## 4. Riscos ou pontos de atenção antes de começar

- **Dependência do backend:** hoje só `GET /health` está implementado. Login, listagem, detalhe e aplicações constam no contrato como **propostas**; a integração real depende da implementação e validação dessas rotas.

- **Alcance da análise:** o contrato não oferece busca textual global nem totais agregados. A interface deve identificar claramente busca, gráfico e contagens quando representarem apenas os registros da página carregada.

- **Limite mínimo de data:** utilizar a menor data existente no banco somente se essa informação já estiver disponível ou puder ser obtida sem aumentar significativamente a complexidade do contrato. Caso contrário, manter apenas a validação entre data inicial e final nesta primeira etapa.

- **Segurança desktop:** manter `contextIsolation` e sandbox ativos, `nodeIntegration` desativado, validar chamadas IPC e renderizar mensagens e stack traces como texto.

[Recomendações do Electron](https://www.electronjs.org/docs/latest/tutorial/security)

- **Premissas da primeira entrega:** Windows, API Docker local na porta 8000, sessão encerrada ao fechar o aplicativo e nenhuma alteração no contrato público. Push em tempo real, busca global, agregações completas e distribuição para outros sistemas ficam para etapas futuras.