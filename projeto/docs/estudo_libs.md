# Estudo de Libs — Agente de Atribuição de Movimento V1

## yfinance

**Uso:** Dados OHLCV, notícias, info de tickers.

```python
import yfinance as yf

tk = yf.Ticker("PETR4.SA")
hist = tk.history(period="60d")
news = tk.news
info = tk.info
```

**Decisões:**
- Suporta tickers `.SA` (B3) e americanos nativamente
- `.news` retorna notícias reais do Yahoo Finance (sem API key)
- Limitação: retorna apenas dados diários na versão gratuita (sem intraday)
- Volume de tickers da B3 pode não ter 100% de cobertura de notícias

---

## langgraph

**Uso:** Orquestração do pipeline como grafo de estados.

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(AgentState)
builder.add_node("fetch", fetch_fn)
builder.add_edge(START, "fetch")
builder.add_edge("fetch", END)
graph = builder.compile()
result = graph.invoke({"ticker": "PETR4.SA", "date": "today"})
```

**Decisões:**
- Fluxo linear (sem condicionais) — suficiente para V1
- Sem checkpointer — V1 não persiste estado
- Sem `bind_tools` — tools são funções puras chamadas nos nós

---

## langchain-ollama + init_chat_model

**Uso:** Comunicação com `gpt-oss:20b-cloud` via Ollama local.

```python
from langchain.chat_models import init_chat_model

llm = init_chat_model(model="gpt-oss:20b-cloud", model_provider="ollama", configurable_fields="any")
response = llm.invoke([SystemMessage(...), HumanMessage(...)])
```

**Decisões:**
- `configurable_fields="any"` permite trocar modelo/temperatura em runtime
- Ollama roda local — sem custo de API
- `gpt-oss:20b-cloud` escolhido pelo balanço performance/custo

---

## pydantic

**Uso:** Validação de entrada (AgentInput) e schema de saída (AgentOutput).

```python
class AgentOutput(BaseModel):
    price_change_pct: float
    movement_type: Literal["macro", "setorial", "company_specific", "technical_flow"]
    confidence: Literal["high", "medium", "low"]
```

**Decisões:**
- Validação em runtime garante contratos do PRD (seção 10)
- Fields com `description` servem como documentação viva

---

## pandas

**Uso:** Cálculos de SMA, médias, volume ratio.

```python
series = pd.Series(closes)
sma20 = series.rolling(20).mean().iloc[-1]
sma50 = series.rolling(50).mean().iloc[-1]
```

**Decisões:**
- Usado internamente nas tools, não exposto ao LLM
- Necessário para rolling window (SMA) e estatísticas

---

## rich

**Uso:** Print formatado no terminal (debug e output final).

```python
from rich.console import Console
from rich.panel import Panel

console = Console()
console.print(Panel("...", title="📊 Métricas"))
```
