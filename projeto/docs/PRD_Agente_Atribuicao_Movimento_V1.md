# PRD --- Agente de Atribuição de Movimento (V1)

## 1. Visão do Produto

Construir um agente em LangGraph que, dado um ticker e uma data (ou
"hoje"), explique o movimento diário de preço usando:

-   Dados diários do Yahoo Finance
-   Análise de índice
-   Análise setorial
-   Tendência de mercado
-   Notícias recentes
-   Classificação estruturada de causa

------------------------------------------------------------------------

## 2. Objetivo da V1

Responder:

> "Por que \[TICKER\] subiu/caiu X% em \[DATA\]?"

Com:

1.  Classificação do tipo de movimento
2.  Atribuição básica de causa
3.  Nível de confiança
4.  Explicação textual baseada nos dados

------------------------------------------------------------------------

## 3. Stack Técnica

| Componente | Tecnologia | Detalhes |
|---|---|---|
| **LLM** | `gpt-oss:20b-cloud` | Via Ollama local |
| **Orquestração** | LangGraph ≥0.4 | StateGraph com fluxo linear |
| **Framework LLM** | LangChain ≥0.3 | `init_chat_model`, Messages |
| **Dados de Mercado** | yfinance ≥0.2.50 | OHLCV, notícias, sem API key |
| **Validação** | Pydantic ≥2.0 | Schemas de I/O |
| **Cálculos** | Pandas ≥2.0 | SMA, rolling, estatísticas |
| **Output** | Rich ≥13.0 | UI de terminal formatada |

------------------------------------------------------------------------

## 4. Escopo

### Incluído

-   Dados diários (OHLC + volume)
-   Dados do índice principal (ex: ^BVSP, ^GSPC dependendo do ticker)
-   Proxy de setor (ETF setorial americano como XLE, XLF, XLK)
-   Notícias recentes via Yahoo Finance
-   Tendência de mercado (curto prazo via SMA)
-   Output estruturado em JSON + explicação textual
-   Arquitetura controlada via LangGraph
-   Modo Interativo Conversacional (V1.2) via ReAct Agent + MemorySaver
-   CLI com argumentos flexíveis (ticker opcional para acionar chat)

### Não incluído

-   Intraday
-   Backtest
-   Probabilidade estatística formal
-   Multi-agente
-   Persistência de estado (além da memória de sessão local do MemorySaver)

------------------------------------------------------------------------

## 5. Definição de Entrada

### Input do usuário

-   `ticker` — Símbolo do ativo (ex: `PETR4.SA`, `AAPL`)
-   `data` — (opcional, default = último pregão) formato `YYYY-MM-DD` ou `today`

Exemplo:

``` json
{
  "ticker": "PETR4.SA",
  "data": "2025-02-18"
}
```

------------------------------------------------------------------------

## 6. Definição de Saída

### JSON estruturado

``` json
{
  "price_change_pct": -3.2,
  "index_change_pct": -0.8,
  "sector_change_pct": -1.5,
  "market_trend": "downtrend",
  "volume_anomaly": true,
  "movement_type": "company_specific",
  "primary_hypothesis": "Notícia corporativa negativa",
  "confidence": "medium",
  "explanation": "O ativo PETR4.SA caiu -3.2% enquanto o Ibovespa recuou apenas -0.8%..."
}
```

- `explanation` — explicação textual detalhada gerada pelo LLM

------------------------------------------------------------------------

## 7. Hipóteses Suportadas (V1)

O agente só pode classificar dentro dessas categorias:

| Tipo | Condição | Exemplo |
|---|---|---|
| **macro** | \|ativo - índice\| < 1.5% | Ativo acompanha o mercado |
| **setorial** | \|ativo - setor\| < 1.5% | Ativo acompanha o setor |
| **company_specific** | Descolado de índice e setor | Notícia corporativa |
| **technical_flow** | Volume anômalo sem causa clara | Fluxo institucional |

------------------------------------------------------------------------

## 8. Definições Técnicas

### 8.1 Thresholds Configurados

``` python
THRESHOLDS = {
    "systemic_delta": 1.5,     # |ativo - índice| < 1.5% → macro
    "sector_delta": 1.5,       # |ativo - setor| < 1.5% → setorial
    "volume_anomaly": 1.8,     # volume/avg_20d > 1.8 → anomalia
    "sma_short": 20,           # Janela SMA curta
    "sma_long": 50,            # Janela SMA longa
    "history_days": 60,        # Dias de histórico
}
```

### 8.2 Movimento Sistêmico (Macro)

Se |ativo - índice| < `systemic_delta` → classificar como **macro**

### 8.3 Movimento Setorial

Se |ativo - setor| < `sector_delta` → classificar como **setorial**

### 8.4 Movimento Específico

Se ativo diverge significativamente de índice e setor → **company_specific**

### 8.5 Volume Anormal

`volume_dia / média_volume_20d > volume_anomaly` → marcar anomalia

### 8.6 Tendência de Mercado

SMA20 vs SMA50 do índice:
- SMA20 > SMA50 * 1.005 → **uptrend**
- SMA20 < SMA50 * 0.995 → **downtrend**
- Caso contrário → **sideways**

------------------------------------------------------------------------

## 9. Arquitetura no LangGraph

### Estado Global (`AgentState`)

``` python
class AgentState(TypedDict):
    ticker: str
    date: str
    stock_data: dict
    index_data: dict
    sector_data: dict
    news: list[dict]
    metrics: dict
    classification: dict
    explanation: str
```

### Nós do Grafo (fluxo linear)

```
START → fetch_stock_data → fetch_index_data → fetch_sector_data → fetch_news
      → compute_metrics → classify_movement → generate_explanation → END
```

O LLM é usado **apenas** no nó `generate_explanation`.
Os demais nós são funções puras (determinísticas).

------------------------------------------------------------------------

## 10. Tools (funções de dados)

| Tool | Entrada | Saída |
|---|---|---|
| `fetch_price_history` | `ticker, days` | Dict OHLCV |
| `fetch_ticker_news` | `ticker, max_results` | List de notícias |
| `compute_statistical_metrics` | `stock, index, sector, date` | Dict de métricas |

> O LLM não acessa API diretamente. Ele recebe dados estruturados do grafo.

------------------------------------------------------------------------

## 11. Critérios de Sucesso

O agente:

-   Nunca responde sem dados quantitativos
-   Sempre produz JSON válido
-   Sempre classifica dentro das 4 categorias
-   Nunca inventa números
-   Sempre cita os valores numéricos na explicação

------------------------------------------------------------------------

## 12. Limitações Conhecidas

-   Setor aproximado por ETF americano (proxy)
-   Notícias podem não capturar todos os eventos relevantes
-   Classificação é heurística, não probabilística
-   Depende de Ollama rodando local com o modelo carregado

------------------------------------------------------------------------

## 13. Roadmap Pós-V1

### V2

-   Geração de hipóteses concorrentes
-   Score probabilístico
-   Avaliação histórica automática

### V3

-   Intraday
-   Sistema adaptativo
