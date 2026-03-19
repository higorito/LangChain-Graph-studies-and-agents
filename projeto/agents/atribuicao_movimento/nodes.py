from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from projeto.agent_base import load_llm
from projeto.agents.atribuicao_movimento.prompts import (
    HUMAN_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_EXPLANATION,
)
from projeto.config import THRESHOLDS, get_ticker_mapping
from projeto.schemas import AgentOutput
from projeto.state import AgentState
from projeto.tools.yahoo_finance import (
    compute_statistical_metrics,
    fetch_price_history,
    fetch_ticker_news,
)


class DataQualityError(ValueError):
    """Erro de qualidade/consistencia dos dados de mercado."""


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
    _validate_market_data_payload("stock_data", state.stock_data)
    _validate_market_data_payload("index_data", state.index_data)
    _validate_market_data_payload("sector_data", state.sector_data)

    target_date = state.date
    if target_date == "today":
        stock_dates = state.stock_data.get("dates", [])
        target_date = stock_dates[-1] if stock_dates else datetime.now().strftime("%Y-%m-%d")
    elif target_date not in state.stock_data.get("dates", []):
        raise DataQualityError(
            f"Data solicitada {target_date} nao encontrada em stock_data para {state.ticker}."
        )

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
            movement_type, hypothesis = "macro", "Movimento alinhado ao mercado geral"
            confidence = "high" if delta_idx < 0.5 else "medium"
        case _ if delta_sec < THRESHOLDS["sector_delta"]:
            movement_type, hypothesis = "setorial", "Movimento alinhado ao setor"
            confidence = "high" if delta_sec < 0.5 else "medium"
        case _ if m["volume_anomaly"] and delta_idx > THRESHOLDS["systemic_delta"]:
            movement_type = "technical_flow"
            hypothesis = "Fluxo atipico de capital - volume anormal sem alinhamento com mercado"
            confidence = "low"
        case _:
            movement_type = "company_specific"
            hypothesis = "Movimento especifico da empresa - descolado do mercado e setor"
            confidence = "medium" if state.news else "low"

    canonical_movement_type = _normalize_movement_type(movement_type)
    return {
        "classification": {
            "movement_type": canonical_movement_type,
            "primary_hypothesis": hypothesis,
            "confidence": confidence,
            "delta_index": round(delta_idx, 2),
            "delta_sector": round(delta_sec, 2),
        }
    }


def generate_explanation(state: AgentState, config: RunnableConfig) -> dict:
    mapping = get_ticker_mapping(state.ticker)
    metrics = state.metrics
    classification = state.classification
    news_text = _format_news(state.news) if state.news else "Nenhuma noticia recente encontrada."

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
    try:
        llm = load_llm(config=config)
        response = llm.invoke(messages, config=config)
        explanation_text = _message_to_text(response)
    except Exception:
        explanation_text = _build_fallback_explanation(state)

    if not explanation_text:
        explanation_text = _build_fallback_explanation(state)

    structured_output = AgentOutput(
        price_change_pct=float(metrics["price_change_pct"]),
        index_change_pct=float(metrics["index_change_pct"]),
        sector_change_pct=float(metrics["sector_change_pct"]),
        market_trend=metrics["market_trend"],
        volume_anomaly=bool(metrics["volume_anomaly"]),
        movement_type=_normalize_movement_type(classification["movement_type"]),
        primary_hypothesis=classification["primary_hypothesis"],
        confidence=classification["confidence"],
        explanation=explanation_text,
    )
    return {"explanation": structured_output.model_dump_json(indent=2)}


def _format_news(news: list[dict]) -> str:
    return "\n".join(
        f"{i}. **{n.get('title', 'Sem titulo')}** - {n.get('publisher', '?')} ({n.get('publish_time', '?')})"
        for i, n in enumerate(news, 1)
    )


def _message_to_text(response: object) -> str:
    content = response.content if hasattr(response, "content") else str(response)
    if isinstance(content, list):
        return "".join(
            block.get("text", str(block)) if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content).strip()


def _normalize_movement_type(value: str) -> str:
    raw = (value or "").strip().lower()
    aliases = {
        "setorial": "setorial",
        "sectorial": "setorial",
    }
    normalized = aliases.get(raw, raw)
    allowed = {"macro", "setorial", "company_specific", "technical_flow"}
    if normalized not in allowed:
        raise ValueError(f"movement_type invalido: {value!r}")
    return normalized


def _validate_market_data_payload(source_name: str, data: dict) -> None:
    if not isinstance(data, dict):
        raise DataQualityError(f"{source_name} invalido: payload nao e dict.")

    upstream_error = data.get("error")
    if upstream_error:
        raise DataQualityError(f"{source_name} retornou erro: {upstream_error}")

    dates = data.get("dates", [])
    closes = data.get("close", [])

    if not isinstance(dates, list) or not isinstance(closes, list):
        raise DataQualityError(f"{source_name} invalido: 'dates' e 'close' devem ser listas.")
    if len(dates) < 2 or len(closes) < 2:
        raise DataQualityError(
            f"{source_name} insuficiente: necessario ao menos 2 pontos em 'dates' e 'close'."
        )
    if len(dates) != len(closes):
        raise DataQualityError(
            f"{source_name} inconsistente: tamanho de 'dates' ({len(dates)}) difere de 'close' ({len(closes)})."
        )

    if source_name == "stock_data":
        volumes = data.get("volume", [])
        if not isinstance(volumes, list):
            raise DataQualityError("stock_data invalido: 'volume' deve ser lista.")
        if len(volumes) != len(dates):
            raise DataQualityError(
                f"stock_data inconsistente: tamanho de 'volume' ({len(volumes)}) difere de 'dates' ({len(dates)})."
            )


def _build_fallback_explanation(state: AgentState) -> str:
    m = state.metrics
    c = state.classification
    return (
        f"No dia {state.date}, o ativo {state.ticker} variou {m['price_change_pct']:.2f}%, "
        f"enquanto o indice variou {m['index_change_pct']:.2f}% e o setor {m['sector_change_pct']:.2f}%. "
        f"A classificacao foi {c['movement_type']} com confianca {c['confidence']}. "
        f"O volume ratio foi {m['volume_ratio']:.2f}x e a tendencia de mercado foi {m['market_trend']}."
    )
