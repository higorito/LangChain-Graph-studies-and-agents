from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from projeto.config import THRESHOLDS, get_ticker_mapping
from projeto.schemas import AgentOutput
from projeto.state import AgentState
from projeto.tools.yahoo_finance import (
    compute_statistical_metrics,
    fetch_price_history,
    fetch_ticker_news,
)
from projeto.agent_base import load_structured_llm, load_llm
from projeto.agents.atribuicao_movimento.prompts import (
    HUMAN_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_EXPLANATION,
)


def fetch_stock_data(state: AgentState) -> dict:
    return {"stock_data": fetch_price_history(state.ticker, target_date=state.date)}


def fetch_index_data(state: AgentState) -> dict:
    mapping = get_ticker_mapping(state.ticker)
    return {"index_data": fetch_price_history(mapping["index"], target_date=state.date)}


def fetch_sector_data(state: AgentState) -> dict:
    mapping = get_ticker_mapping(state.ticker)
    return {"sector_data": fetch_price_history(mapping["sector_etf"], target_date=state.date)}


def fetch_news(state: AgentState) -> dict:
    return {"news": fetch_ticker_news(state.ticker, max_results=5)}


def compute_metrics(state: AgentState) -> dict:
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


def classify_movement(state: AgentState) -> dict:
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


def generate_explanation(state: AgentState, config: RunnableConfig) -> dict:
    mapping = get_ticker_mapping(state.ticker)
    metrics = state.metrics
    classification = state.classification
    news_text = _format_news(state.news) if state.news else "Nenhuma notícia recente encontrada."
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
    clean_config = {"configurable": config.get("configurable", {})}
    structured_llm = load_structured_llm(AgentOutput, config=clean_config)
    try:
        result: AgentOutput = structured_llm.invoke(messages, config=clean_config)
        explanation = result.model_dump_json(indent=2)
    except Exception:
        llm = load_llm(config=clean_config)
        response = llm.invoke(messages, config=clean_config)
        explanation = response.content if hasattr(response, "content") else str(response)
    return {"explanation": explanation}


def _format_news(news: list[dict]) -> str:
    return "\n".join(
        f"{i}. **{n.get('title', 'Sem título')}** — {n.get('publisher', '?')} ({n.get('publish_time', '?')})"
        for i, n in enumerate(news, 1)
    )
