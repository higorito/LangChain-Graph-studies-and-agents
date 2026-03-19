"""
Ferramentas expostas ao agente conversacional (modo chat).
Dependem de contexto (LLM/model/provider) injetado via modulo interactive.
"""

from concurrent.futures import ThreadPoolExecutor
import json

from langchain_core.tools import tool

from projeto.config import (
    resolve_ticker,
    ensure_yahoo_ticker,
    ticker_has_market_data,
    TICKER_ALIASES,
)


def _get_llm():
    from projeto.interactive_llm import get_active_llm

    return get_active_llm()


def _get_model_provider():
    from projeto.interactive_llm import get_active_model_provider

    return get_active_model_provider()


def _run_agent(ticker: str, date: str, model: str | None, provider: str | None) -> dict:
    from projeto.main import run_agent

    return run_agent(ticker=ticker, date=date, model=model, provider=provider, silent=True)


def _sanitize_ticker(value: str | None) -> str:
    text = str(value or "").strip().upper()
    text = text.strip("\"'").replace("$", "").strip(",.;:")
    return text.split()[0] if text else ""


def _should_try_llm_resolution(original_input: str, resolved: str) -> bool:
    if not resolved:
        return True
    if resolved in TICKER_ALIASES.values():
        return False

    input_norm = _sanitize_ticker(original_input)
    baseline = ensure_yahoo_ticker(input_norm)
    return resolved in {input_norm, baseline}


def _resolve_with_fallback(value: str) -> str:
    resolved = ensure_yahoo_ticker(resolve_ticker(value))
    if ticker_has_market_data(resolved):
        return resolved

    if not _should_try_llm_resolution(value, resolved):
        return resolved

    llm = _get_llm()
    if not llm:
        return resolved

    try:
        from pydantic import BaseModel

        class TickerSuggestion(BaseModel):
            ticker: str

        result = llm.with_structured_output(TickerSuggestion).invoke(
            f'Dado o nome ou ticker "{value}", retorne apenas o ticker de bolsa no formato Yahoo Finance. '
            "Brasil: use .SA (ex: PETR4.SA, VALE3.SA). EUA: simbolo puro (ex: AAPL). "
            "Retorne apenas o ticker."
        )
        candidate = ensure_yahoo_ticker(_sanitize_ticker(result.ticker))
        if candidate and ticker_has_market_data(candidate):
            return candidate
    except Exception:
        pass

    return resolved


@tool
def resolver_ticker(nome_ou_ticker: str) -> str:
    """Resolve nome de empresa ou ticker para o simbolo oficial no formato Yahoo."""
    resolved = _resolve_with_fallback(nome_ou_ticker)
    return json.dumps({"ticker": resolved, "entrada": nome_ou_ticker})


@tool
def analisar_acao(ticker: str, data: str = "today") -> str:
    """Analisa um unico ativo e retorna um resumo enxuto. Nao use para comparar dois ativos."""
    resolved = _resolve_with_fallback(ticker)
    model, provider = _get_model_provider()
    try:
        resultado = _run_agent(ticker=resolved, date=data, model=model, provider=provider)
        return json.dumps(_compact_analysis_result(resultado, resolved), indent=2)
    except Exception as e:
        return json.dumps({"erro": str(e), "ticker": resolved})


@tool
def comparar_ativos(ticker1: str, ticker2: str, data: str = "today") -> str:
    """Use sempre para comparar dois ativos na mesma pergunta. Evita duas analises separadas."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        resolved_futures = [
            executor.submit(_resolve_with_fallback, ticker1),
            executor.submit(_resolve_with_fallback, ticker2),
        ]
        r1, r2 = [future.result() for future in resolved_futures]

    model, provider = _get_model_provider()

    with ThreadPoolExecutor(max_workers=2) as executor:
        run_futures = [
            executor.submit(_run_agent_safe, r1, data, model, provider),
            executor.submit(_run_agent_safe, r2, data, model, provider),
        ]
        (res1, err1), (res2, err2) = [future.result() for future in run_futures]

    if err1 and err2:
        return json.dumps(
            {
                "erro": "Nao foi possivel analisar os dois ativos.",
                "detalhes": {
                    ticker1: {"ticker_resolvido": r1, "erro": err1},
                    ticker2: {"ticker_resolvido": r2, "erro": err2},
                },
            },
            indent=2,
        )

    summary1 = _compact_analysis_result(res1, r1)
    summary2 = _compact_analysis_result(res2, r2)
    out = {
        "data": summary1.get("data", summary2.get("data", data)),
        ticker1: {
            "ticker_resolvido": r1,
            "erro": err1,
            "variacao_pct": summary1.get("variacao_pct"),
            "tipo_movimento": summary1.get("tipo_movimento"),
            "hipotese": summary1.get("hipotese"),
            "confianca": summary1.get("confianca"),
            "preco_fechamento": summary1.get("preco_fechamento"),
        },
        ticker2: {
            "ticker_resolvido": r2,
            "erro": err2,
            "variacao_pct": summary2.get("variacao_pct"),
            "tipo_movimento": summary2.get("tipo_movimento"),
            "hipotese": summary2.get("hipotese"),
            "confianca": summary2.get("confianca"),
            "preco_fechamento": summary2.get("preco_fechamento"),
        },
    }
    return json.dumps(out, indent=2)


def _run_agent_safe(
    ticker: str,
    date: str,
    model: str | None,
    provider: str | None,
) -> tuple[dict, str | None]:
    try:
        return _run_agent(ticker=ticker, date=date, model=model, provider=provider), None
    except Exception as error:
        return {}, str(error)


def _compact_analysis_result(resultado: dict, ticker: str) -> dict:
    metrics = resultado.get("metrics", {})
    classification = resultado.get("classification", {})
    news = resultado.get("news") or []
    closes = (resultado.get("stock_data") or {}).get("close") or []

    headlines = [
        item.get("title")
        for item in news
        if isinstance(item, dict) and item.get("title")
    ][:3]

    return {
        "ticker": ticker,
        "data": resultado.get("date", "today"),
        "preco_fechamento": closes[-1] if closes else None,
        "variacao_pct": metrics.get("price_change_pct"),
        "variacao_indice_pct": metrics.get("index_change_pct"),
        "variacao_setor_pct": metrics.get("sector_change_pct"),
        "market_trend": metrics.get("market_trend"),
        "anomalia_volume": metrics.get("volume_anomaly"),
        "volume_ratio": metrics.get("volume_ratio"),
        "tipo_movimento": classification.get("movement_type"),
        "hipotese": classification.get("primary_hypothesis"),
        "confianca": classification.get("confidence"),
        "explicacao": _extract_explanation(resultado.get("explanation")),
        "manchetes": headlines,
    }


def _extract_explanation(raw_explanation: object) -> str:
    if not isinstance(raw_explanation, str):
        return str(raw_explanation or "")

    try:
        parsed = json.loads(raw_explanation)
    except json.JSONDecodeError:
        return raw_explanation

    if isinstance(parsed, dict):
        return str(parsed.get("explanation", raw_explanation))
    return raw_explanation
