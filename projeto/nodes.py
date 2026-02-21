"""
Nós do grafo LangGraph — Agente de Atribuição de Movimento V1.

Padrões modernos utilizados:
- with_structured_output + Pydantic → output validado sem parse manual
- Nós de fetch são independentes e rodam em paralelo (fan-out/fan-in)
- Apenas generate_explanation usa LLM — demais nós são funções puras

Fluxo:
    START ──┬── fetch_stock_data ──┐
            ├── fetch_index_data ──┤
            ├── fetch_sector_data ─┤── compute_metrics → classify → explain → END
            └── fetch_news ────────┘
"""
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from projeto.config import THRESHOLDS, get_ticker_mapping
from projeto.prompts import HUMAN_PROMPT_TEMPLATE, SYSTEM_PROMPT_EXPLANATION
from projeto.schemas import AgentOutput
from projeto.state import AgentState
from projeto.tools.yahoo_finance import (
    compute_statistical_metrics,
    fetch_price_history,
    fetch_ticker_news,
)
from projeto.utils import load_structured_llm


# Nós de Fetch (independentes — rodam em paralelo via fan-out)

def fetch_stock_data(state: AgentState) -> dict:
    """Busca dados OHLCV do ticker-alvo."""
    return {"stock_data": fetch_price_history(state.ticker, target_date=state.date)}


def fetch_index_data(state: AgentState) -> dict:
    """Busca dados OHLCV do índice de referência (^BVSP ou ^GSPC)."""
    mapping = get_ticker_mapping(state.ticker)
    return {"index_data": fetch_price_history(mapping["index"], target_date=state.date)}


def fetch_sector_data(state: AgentState) -> dict:
    """Busca dados OHLCV do ETF setorial (proxy de setor)."""
    mapping = get_ticker_mapping(state.ticker)
    return {"sector_data": fetch_price_history(mapping["sector_etf"], target_date=state.date)}


def fetch_news(state: AgentState) -> dict:
    """Busca notícias recentes do ticker via Yahoo Finance."""
    return {"news": fetch_ticker_news(state.ticker, max_results=5)}


# Nó de Cálculo

def compute_metrics(state: AgentState) -> dict:
    """Calcula métricas estatísticas a partir dos dados fetched."""
    target_date = state.date

    if target_date == "today":
        stock_dates = state.stock_data.get("dates", [])
        target_date = stock_dates[-1] if stock_dates else datetime.now().strftime("%Y-%m-%d")

    metrics = compute_statistical_metrics(
        stock_data=state.stock_data,
        index_data=state.index_data,
        sector_data=state.sector_data,
        target_date=target_date,
    )

    return {"metrics": metrics, "date": target_date}


# Nó de Classificação (heurístico — sem LLM)

def classify_movement(state: AgentState) -> dict:
    """Classifica o tipo de movimento baseado em heurísticas.

    Categorias:
    1. macro           → alinhado ao índice
    2. setorial        → alinhado ao setor
    3. technical_flow  → volume anormal sem causa clara
    4. company_specific → descolado de tudo
    """
    m = state.metrics
    price, index, sector = m["price_change_pct"], m["index_change_pct"], m["sector_change_pct"]
    delta_idx, delta_sec = abs(price - index), abs(price - sector)

    match True:
        case _ if delta_idx < THRESHOLDS["systemic_delta"]:
            mv_type, hyp = "macro", "Movimento alinhado ao mercado geral"
            conf = "high" if delta_idx < 0.5 else "medium"

        case _ if delta_sec < THRESHOLDS["sector_delta"]:
            mv_type, hyp = "setorial", "Movimento alinhado ao setor"
            conf = "high" if delta_sec < 0.5 else "medium"

        case _ if m["volume_anomaly"] and delta_idx > THRESHOLDS["systemic_delta"]:
            mv_type = "technical_flow"
            hyp = "Fluxo atípico de capital — volume anormal sem alinhamento com mercado"
            conf = "low"

        case _:
            mv_type = "company_specific"
            hyp = "Movimento específico da empresa — descolado do mercado e setor"
            conf = "medium" if state.news else "low"

    return {
        "classification": {
            "movement_type": mv_type,
            "primary_hypothesis": hyp,
            "confidence": conf,
            "delta_index": round(delta_idx, 2),
            "delta_sector": round(delta_sec, 2),
        }
    }


# Nó de Geração (LLM com structured output)

def generate_explanation(state: AgentState, config: RunnableConfig) -> dict:
    """Gera a explicação usando LLM + with_structured_output.

    Aceita `config` opcional em runtime, permitindo trocar dinamicamente
    o `model` e `model_provider` sem mexer no código do nó.
    """
    mapping = get_ticker_mapping(state.ticker)
    metrics = state.metrics
    classification = state.classification

    # Formatar notícias
    news_text = _format_news(state.news) if state.news else "Nenhuma notícia recente encontrada."

    # Montar prompt
    human_content = HUMAN_PROMPT_TEMPLATE.format(
        ticker=state.ticker,
        date=state.date,
        price_change_pct=metrics["price_change_pct"],
        index_change_pct=metrics["index_change_pct"],
        index_ticker=mapping["index"],
        sector_change_pct=metrics["sector_change_pct"],
        sector_etf=mapping["sector_etf"],
        volume_ratio=metrics["volume_ratio"],
        volume_anomaly=metrics["volume_anomaly"],
        market_trend=metrics["market_trend"],
        movement_type=classification["movement_type"],
        confidence=classification["confidence"],
        news_text=news_text,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT_EXPLANATION),
        HumanMessage(content=human_content),
    ]

    # Limpar config interno do LangGraph para evitar warnings
    # Apenas enviamos o bloco "configurable" para o LLM, ignorando os campos '__pregel'
    clean_config = {"configurable": config.get("configurable", {})}

    # with_structured_output: retorno Pydantic direto
    structured_llm = load_structured_llm(AgentOutput, config=clean_config)

    try:
        # Repassa o 'config' limpo para sobrescrever modelo/provider se houver
        result: AgentOutput = structured_llm.invoke(messages, config=clean_config)
        explanation = result.model_dump_json(indent=2)
    except Exception as e:
        # Fallback: LLM sem structured output
        from projeto.utils import load_llm
        llm = load_llm(config=clean_config)
        response = llm.invoke(messages, config=clean_config)
        explanation = response.content if hasattr(response, "content") else str(response)

    return {"explanation": explanation}


def _format_news(news: list[dict]) -> str:
    """Formata lista de notícias para o prompt."""
    return "\n".join(
        f"{i}. **{n.get('title', 'Sem título')}** — {n.get('publisher', '?')} ({n.get('publish_time', '?')})"
        for i, n in enumerate(news, 1)
    )
