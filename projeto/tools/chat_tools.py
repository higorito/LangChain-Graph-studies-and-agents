"""
Ferramentas expostas ao agente conversacional (modo chat).
Dependem de contexto (LLM/model/provider) injetado via modulo interactive.
"""

import json

from langchain_core.tools import tool

from projeto.config import (
    resolve_ticker,
    ensure_yahoo_ticker,
    ticker_has_market_data,
    TICKER_ALIASES,
)


def _get_llm():
    from projeto.interactive import _get_llm as get_llm

    return get_llm()


def _get_model_provider():
    from projeto.interactive import _get_model_provider as get_mp

    return get_mp()


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
    """Executa a analise completa para um ativo."""
    resolved = _resolve_with_fallback(ticker)
    model, provider = _get_model_provider()
    try:
        resultado = _run_agent(ticker=resolved, date=data, model=model, provider=provider)
        closes = (resultado.get("stock_data") or {}).get("close") or []
        if closes:
            resultado = dict(resultado)
            resultado["preco_fechamento"] = closes[-1]
        return json.dumps(resultado, indent=2)
    except Exception as e:
        return json.dumps({"erro": str(e), "ticker": resolved})


@tool
def comparar_ativos(ticker1: str, ticker2: str, data: str = "today") -> str:
    """Compara dois ativos na mesma data."""
    r1 = _resolve_with_fallback(ticker1)
    r2 = _resolve_with_fallback(ticker2)
    model, provider = _get_model_provider()

    err1 = None
    err2 = None
    try:
        res1 = _run_agent(ticker=r1, date=data, model=model, provider=provider)
    except Exception as e:
        res1 = {}
        err1 = str(e)

    try:
        res2 = _run_agent(ticker=r2, date=data, model=model, provider=provider)
    except Exception as e:
        res2 = {}
        err2 = str(e)

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

    m1 = res1.get("metrics", {})
    m2 = res2.get("metrics", {})
    c1 = res1.get("classification", {})
    c2 = res2.get("classification", {})
    out = {
        "data": res1.get("date", res2.get("date", data)),
        ticker1: {
            "ticker_resolvido": r1,
            "erro": err1,
            "variacao_pct": m1.get("price_change_pct"),
            "tipo_movimento": c1.get("movement_type"),
            "hipotese": c1.get("primary_hypothesis"),
        },
        ticker2: {
            "ticker_resolvido": r2,
            "erro": err2,
            "variacao_pct": m2.get("price_change_pct"),
            "tipo_movimento": c2.get("movement_type"),
            "hipotese": c2.get("primary_hypothesis"),
        },
    }
    return json.dumps(out, indent=2)
