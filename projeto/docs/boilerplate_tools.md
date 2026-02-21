# Boilerplate de Tools — Retornos e Exemplos

## fetch_price_history

**Assinatura:** `fetch_price_history(ticker: str, days: int = 60) -> dict`

**Retorno esperado:**
```json
{
  "ticker": "PETR4.SA",
  "dates": ["2025-02-10", "2025-02-11", "2025-02-12", "..."],
  "open":   [36.50, 36.80, 37.10],
  "high":   [37.20, 37.50, 37.80],
  "low":    [36.30, 36.60, 36.90],
  "close":  [36.90, 37.20, 37.50],
  "volume": [25000000, 30000000, 28000000]
}
```

**Caso de erro (ticker inválido):**
```json
{
  "ticker": "INVALIDO",
  "dates": [],
  "open": [], "high": [], "low": [], "close": [], "volume": [],
  "error": "Nenhum dado encontrado para INVALIDO"
}
```

---

## fetch_ticker_news

**Assinatura:** `fetch_ticker_news(ticker: str, max_results: int = 5) -> list[dict]`

**Retorno esperado:**
```json
[
  {
    "title": "Petrobras anuncia dividendos extraordinários",
    "publisher": "InfoMoney",
    "link": "https://...",
    "publish_time": "2025-02-18T14:30:00Z"
  }
]
```

**Caso sem notícias:** `[]`

---

## compute_statistical_metrics

**Assinatura:**
```python
compute_statistical_metrics(
    stock_data: dict,     # output de fetch_price_history
    index_data: dict,     # output de fetch_price_history (índice)
    sector_data: dict,    # output de fetch_price_history (ETF)
    target_date: str      # "YYYY-MM-DD"
) -> dict
```

**Retorno esperado:**
```json
{
  "price_change_pct": -3.2,
  "index_change_pct": -0.8,
  "sector_change_pct": -1.5,
  "volume_ratio": 2.3,
  "volume_anomaly": true,
  "market_trend": "downtrend"
}
```

---

## Fluxo de Dados Completo

```
Input: {"ticker": "PETR4.SA", "date": "today"}
    │
    ├──→ fetch_stock_data   → stock_data (OHLCV PETR4.SA)
    ├──→ fetch_index_data   → index_data (OHLCV ^BVSP)
    ├──→ fetch_sector_data  → sector_data (OHLCV XLE)
    ├──→ fetch_news         → news (lista de notícias)
    │
    ├──→ compute_metrics    → metrics (variações, volume, trend)
    ├──→ classify_movement  → classification (tipo, hipótese, confiança)
    │
    └──→ generate_explanation → explanation (JSON do LLM)
```
