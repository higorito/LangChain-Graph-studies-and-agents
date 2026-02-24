# PRD - Agente de Atribuicao de Movimento (V1)

Data de atualizacao deste PRD: 2026-02-24

## 1. Visao do Produto

Construir um agente em LangGraph que, dado um ticker e uma data (ou `today`), explique o movimento diario de preco usando:

- Dados diarios do Yahoo Finance
- Analise de indice
- Analise setorial (proxy ETF)
- Tendencia de mercado (SMA)
- Noticias recentes
- Classificacao estruturada de causa

## 2. Objetivo da V1

Responder:

> "Por que [TICKER] subiu/caiu X% em [DATA]?"

Com:

1. Classificacao do tipo de movimento
2. Atribuicao basica de causa
3. Nivel de confianca
4. Explicacao textual baseada em dados

## 3. Estado Atual Implementado

### 3.1 Modos de uso

- `run`: analise one-shot por ticker/data
- `chat`: modo conversacional com ferramentas e memoria

### 3.2 Stack atual no codigo

| Componente | Tecnologia | Observacao |
|---|---|---|
| LLM | LangChain `init_chat_model` | Provider/model configuraveis em runtime |
| Providers | Ollama, Google GenAI, OpenRouter | Default atual: `ollama` + `gpt-oss:20b-cloud` |
| Orquestracao | LangGraph >=0.4 | `StateGraph` |
| Dados de mercado | yfinance >=0.2.50 | OHLCV + noticias |
| Validacao | Pydantic >=2.0 | `InputState`, `OutputState`, `AgentOutput` |
| Calculos | Pandas >=2.0 | SMA, variacoes, ratio de volume |
| UI terminal | Rich >=13.0 | paineis e progresso de nos |

## 4. Escopo

### Incluido na V1

- Dados diarios (OHLCV)
- Indice de referencia por mapeamento de ticker
- Proxy setorial por ETF
- Noticias recentes via Yahoo Finance
- Heuristica de tendencia (SMA20 vs SMA50)
- Classificacao em 4 categorias
- Explicacao por LLM com base nos dados computados
- CLI com `run` e `chat`
- Modo chat com ferramentas:
  - `analisar_acao`
  - `comparar_ativos`
  - `resolver_ticker`
- Checkpoint de conversa:
  - `memory` (padrao)
  - `sqlite` (opcional)
  - `postgres` (opcional)

### Fora de escopo (V1)

- Intraday
- Backtest
- Modelo probabilistico formal
- Multi-agente especializado
- Garantia de persistencia sem configurar checkpoint

## 5. Entrada

### Input principal (`run`)

- `ticker`: simbolo do ativo (ex: `PETR4.SA`, `AAPL`)
- `date`: `YYYY-MM-DD` ou `today` (default)
- `model` (opcional)
- `provider` (opcional)

Exemplo:

```json
{
  "ticker": "PETR4.SA",
  "date": "2025-02-18"
}
```

## 6. Saida

### Saida funcional do pipeline

- `ticker`
- `date`
- `metrics`
- `classification`
- `explanation`

Campos de `metrics`:

- `price_change_pct`
- `index_change_pct`
- `sector_change_pct`
- `volume_ratio`
- `volume_anomaly`
- `market_trend`

Campos de `classification`:

- `movement_type` em: `macro`, `setorial`, `company_specific`, `technical_flow`
- Padrao canonico: `setorial` (entrada `sectorial` e normalizada para `setorial`)
- `primary_hypothesis`
- `confidence` em: `high`, `medium`, `low`
- `delta_index`
- `delta_sector`

### Observacao importante sobre formato da explicacao

O no `generate_explanation` sempre monta e valida o `AgentOutput` final (JSON estruturado).  
A explicacao textual do LLM e incorporada nesse objeto validado.

## 7. Heuristicas e Thresholds

Configuracao atual:

```python
THRESHOLDS = {
    "systemic_delta": 1.5,
    "sector_delta": 1.5,
    "volume_anomaly": 1.8,
    "sma_short": 20,
    "sma_long": 50,
    "history_days": 60,
}
```

Regras de classificacao (ordem de decisao):

1. `macro`: `abs(price - index) < systemic_delta`
2. `setorial`: `abs(price - sector) < sector_delta`
3. `technical_flow`: volume anomalo e descolamento do indice
4. `company_specific`: fallback

Regras de tendencia:

- `uptrend`: `SMA20 > SMA50 * 1.005`
- `downtrend`: `SMA20 < SMA50 * 0.995`
- `sideways`: caso contrario

## 8. Arquitetura LangGraph (Implementacao Atual)

Fluxo atual (fan-out paralelo de coleta, depois juncao):

```text
START -> fetch_stock_data ----\
START -> fetch_index_data -----+-> compute_metrics -> classify_movement -> generate_explanation -> END
START -> fetch_sector_data ----/
START -> fetch_news ----------/
```

Detalhes implementados:

- Retry policy de ate 3 tentativas nos nos de coleta:
  - `fetch_stock_data`
  - `fetch_index_data`
  - `fetch_sector_data`
  - `fetch_news`
- LLM usado apenas em `generate_explanation` no fluxo `run`

## 9. O que faltava no PRD e ja estava implementado

1. Multi-provider e override por CLI (`--provider`, `--model`)
2. Modo `chat` com ferramentas reais (`analisar_acao`, `comparar_ativos`, `resolver_ticker`)
3. Checkpoint de conversa com `memory/sqlite/postgres` e `thread_id`
4. Retry nos nos de fetch
5. Fan-out paralelo no grafo (nao linear)
6. Fallback deterministico de explicacao mantendo saida JSON valida
7. Resolucao de ticker por nome (no modo chat e utilitarios de config)

## 10. Gaps entre PRD antigo e codigo atual

1. PRD antigo assumia stack fixa em Ollama; codigo default atual usa OpenRouter.
2. PRD antigo dizia fluxo linear; codigo atual usa paralelizacao de coleta.
3. PRD antigo exigia "sempre JSON valido"; gap resolvido em 2026-02-24 com validacao final de `AgentOutput`.
4. PRD antigo nao detalhava modo chat, tools e opcoes de checkpoint.
5. PRD antigo nao registrava retry policy dos nos de coleta.

## 11. Riscos e limitacoes atuais

1. Se dados vierem vazios do Yahoo, a analise pode degradar para metricas neutras.
2. Classificacao segue heuristica fixa (nao probabilistica).
3. Proxy setorial pode nao representar bem alguns ativos (especialmente fora do mapeamento conhecido).
4. Noticias do Yahoo podem ser incompletas para eventos de alto impacto.

## 12. Proximos passos viaveis (Roadmap)

Implementado em 2026-02-24:
1. Saida final estruturada forcada via `AgentOutput`.
2. Guardrails de qualidade para `dates`/`close` (falha explicita quando insuficiente/inconsistente).
3. Padronizacao de nomenclatura `movement_type` em `setorial`.

### Prioridade P1 (confiabilidade e consistencia)

1. Endurecer validacao de data alvo:
   - Opcionalmente exigir disponibilidade da mesma data em indice/setor.
2. Expor erros de qualidade em formato estruturado:
   - Codigo, causa e sugestao de acao para debug.
3. Tornar fallback de explicacao auditavel:
   - Indicar quando texto veio do LLM vs fallback deterministico.

### Prioridade P2 (qualidade analitica)

1. Melhorar mapeamento de setor:
   - Expandir `TICKER_SECTOR_MAP` e reduzir fallback generico.
2. Enriquecer atribuicao com "evidencias":
   - Citar quais noticias impactaram e porque.
3. Ajustar confianca com score composto:
   - Distancia ativo-indice/setor + anomalia de volume + disponibilidade de noticia.

### Prioridade P3 (engenharia e produto)

1. Suite de testes automatizados:
   - Unitarios para metricas/classificacao
   - Integracao com snapshots/mock de Yahoo
2. Observabilidade:
   - Logging estruturado por no, tempos e falhas
3. Evolucao do chat:
   - Melhor entendimento de data em linguagem natural
   - Politica de reuso de contexto com menos chamadas de ferramenta

## 13. Novas funcionalidades e tools uteis para estudo

### 13.1 Funcionalidades candidatas (alto valor didatico)

1. Modo "explicar decisao do agente":
   - Expor quais sinais pesaram na classificacao (delta indice, delta setor, volume, noticias).
2. Modo "comparacao temporal":
   - Explicar diferenca de comportamento do mesmo ativo em duas datas.
3. Modo "watchlist":
   - Rodar analise em lote para lista de tickers e rankear por descolamento.
4. Modo "evento relevante":
   - Destacar quando houver gap grande + anomalia de volume + noticia forte.
5. Modo "resumo executivo":
   - Saida curta para decisao rapida (3-5 linhas) alem do output detalhado.

### 13.2 Tools novas recomendadas

1. Tool de calendario de mercado:
   - Ajusta automaticamente para ultimo pregao valido por mercado.
2. Tool de fundamentals basicos:
   - Coletar P/L, EV/EBITDA, market cap para contexto da explicacao.
3. Tool de noticias multi-fonte:
   - Complementar Yahoo com outra fonte para reduzir vies de cobertura.
4. Tool de normalizacao de ticker robusta:
   - Resolver ambiguidades por pais/bolsa e validar simbolo antes de executar.
5. Tool de cache persistente:
   - Evitar chamadas repetidas em execucoes proximas e reduzir latencia/custo.

### 13.3 Funcionalidades LangGraph/LangChain para praticar

1. Interrupt e Human-in-the-loop:
   - Pausar o fluxo antes de decisao critica e permitir aprovacao humana.
2. Subgraphs:
   - Separar pipeline de dados, pipeline de classificacao e pipeline de narracao.
3. Memory de longo prazo:
   - Salvar preferencias do usuario e contexto recorrente entre sessoes.
4. Router de estrategia:
   - Escolher dinamicamente fluxo rapido vs fluxo profundo conforme pergunta.

## 14. Conceitos superimportantes para dominar agentes (e ainda parciais no projeto)

1. Contrato estrito de I/O (schema-first):
   - Agente confiavel comeca com contrato forte de entrada/saida.
   - No projeto atual o contrato final ja e estruturado; manter isso e crucial para previsibilidade.
2. Separacao entre decisao e execucao:
   - LLM decide; tools executam.
   - Quanto mais logica deterministica fora do LLM, menor alucinacao e maior testabilidade.
3. Estado explicito e versionado:
   - Cada no deve ler/escrever estado claro e auditavel.
   - Isso facilita replay, debug e evolucao de fluxo sem regressao silenciosa.
4. Observabilidade real de agentes:
   - Traces por no, latencia por etapa, taxa de erro por tool, custo por execucao.
   - Sem observabilidade, agente "funciona" ate quebrar em producao sem diagnostico.
5. Avaliacao sistematica (Agent Evals):
   - Definir dataset de cenarios e metricas de qualidade.
   - Rodar regressao automatica a cada mudanca de prompt, tool ou modelo.
6. Confiabilidade por design:
   - Retry, timeout, fallback controlado e tratamento de dados faltantes.
   - Objetivo: falhar de forma explicita e segura, nao "responder qualquer coisa".
7. Memoria com criterio:
   - Memoria curta (sessao) e longa (preferencias/historico) com regras claras de uso.
   - Evitar tanto perda de contexto quanto contaminacao por contexto antigo.
8. Planejamento e reflexao controlados:
   - Nem todo problema precisa de agente "autonomo".
   - Usar planejar-refletir-revisar apenas onde gera ganho real, para nao aumentar custo/latencia sem retorno.
9. Governanca de ferramentas:
   - Cada tool deve ter escopo claro, validacao de input e semantica estavel.
   - Tool mal definida vira principal fonte de erro em arquiteturas agenticas.
10. Reprodutibilidade:
   - Registrar modelo, provider, parametros e versoes de prompts.
   - Sem isso, resultados mudam e fica dificil aprender de verdade em projeto de estudo.
