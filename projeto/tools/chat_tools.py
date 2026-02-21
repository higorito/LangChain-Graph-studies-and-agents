"""
Ferramentas expostas ao agente conversacional (modo chat).
Dependem de contexto (LLM/model/provider) injetado via módulo interactive.
"""
import json
from langchain_core.tools import tool

from projeto.config import resolve_ticker, ensure_yahoo_ticker, TICKER_SECTOR_MAP


def _get_llm():
    from projeto.interactive import _get_llm as get_llm
    return get_llm()


def _get_model_provider():
    from projeto.interactive import _get_model_provider as get_mp
    return get_mp()


def _run_agent(ticker: str, date: str, model: str | None, provider: str | None) -> dict:
    from projeto.main import run_agent
    return run_agent(ticker=ticker, date=date, model=model, provider=provider, silent=True)


@tool
def resolver_ticker(nome_ou_ticker: str) -> str:
    """Resolve nome de empresa ou ticker para o símbolo oficial na bolsa (formato Yahoo).
    Use quando o usuário mencionar apenas o nome (ex: Petrobras, Nvidia) e você precisar do ticker (PETR4.SA, NVDA).
    Ações brasileiras retornam com sufixo .SA (ex: BBAS3.SA)."""
    resolved = resolve_ticker(nome_ou_ticker)
    if resolved == nome_ou_ticker.upper() and resolved not in TICKER_SECTOR_MAP:
        llm = _get_llm()
        if llm:
            try:
                from pydantic import BaseModel
                class TickerSuggestion(BaseModel):
                    ticker: str
                structured = llm.with_structured_output(TickerSuggestion)
                result = structured.invoke(
                    f'Dado o nome ou ticker "{nome_ou_ticker}", retorne apenas o ticker de bolsa. '
                    'Brasil: sufixo .SA (ex: PETR4.SA). EUA: símbolo (ex: AAPL). Resposta só o ticker.'
                )
                resolved = result.ticker
            except Exception:
                pass
    resolved = ensure_yahoo_ticker(resolved)
    return json.dumps({"ticker": resolved, "entrada": nome_ou_ticker})


@tool
def analisar_acao(ticker: str, data: str = "today") -> str:
    """Executa a análise completa: preço, variação, índice, setor, notícias e explicação do movimento.
    Use para: por que subiu/caiu, preço, notícias, métricas. Aceita ticker (PETR4.SA, NVDA) ou nome (Petrobras, Nvidia).
    Retorna métricas (incl. preço e variação), classificação e notícias recentes."""
    resolved = resolve_ticker(ticker)
    if resolved == ticker.upper() and resolved not in TICKER_SECTOR_MAP:
        llm = _get_llm()
        if llm:
            try:
                from pydantic import BaseModel
                class TickerSuggestion(BaseModel):
                    ticker: str
                result = llm.with_structured_output(TickerSuggestion).invoke(
                    f'Sugira o ticker de bolsa para: "{ticker}". Brasil: .SA. EUA: símbolo. Só o ticker.'
                )
                resolved = result.ticker
            except Exception:
                pass
    resolved = ensure_yahoo_ticker(resolved)
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
    """Compara dois ativos na mesma data: métricas e classificação de movimento.
    Use quando o usuário pedir comparação entre duas ações (ex: Petrobras vs Vale, NVDA vs AAPL).
    Retorna variação percentual, tipo de movimento e resumo de cada um."""
    r1 = ensure_yahoo_ticker(resolve_ticker(ticker1))
    r2 = ensure_yahoo_ticker(resolve_ticker(ticker2))
    model, provider = _get_model_provider()
    try:
        res1 = _run_agent(ticker=r1, date=data, model=model, provider=provider)
        res2 = _run_agent(ticker=r2, date=data, model=model, provider=provider)
    except Exception as e:
        return json.dumps({"erro": str(e)})
    m1 = res1.get("metrics", {})
    m2 = res2.get("metrics", {})
    c1 = res1.get("classification", {})
    c2 = res2.get("classification", {})
    out = {
        "data": res1.get("date", data),
        ticker1: {
            "ticker_resolvido": r1,
            "variacao_pct": m1.get("price_change_pct"),
            "tipo_movimento": c1.get("movement_type"),
            "hipotese": c1.get("primary_hypothesis"),
        },
        ticker2: {
            "ticker_resolvido": r2,
            "variacao_pct": m2.get("price_change_pct"),
            "tipo_movimento": c2.get("movement_type"),
            "hipotese": c2.get("primary_hypothesis"),
        },
    }
    return json.dumps(out, indent=2)
