"""
Tools de acesso ao Yahoo Finance.

Funções puras usadas pelos nós do grafo para buscar e computar dados.
NÃO são chamadas diretamente pelo LLM — o LLM recebe os dados já estruturados.
"""
from datetime import datetime, timedelta
import functools
import logging

import pandas as pd
import yfinance as yf

from projeto.config import THRESHOLDS

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=32)
def fetch_price_history(ticker: str, days: int | None = None, target_date: str | None = None) -> dict:
    """Busca histórico OHLCV de um ticker via Yahoo Finance.

    Args:
        ticker: Símbolo do ativo (ex: "PETR4.SA", "AAPL", "^BVSP")
        days: Número de dias de histórico. Default: THRESHOLDS["history_days"]
        target_date: Data limite no formato "YYYY-MM-DD" ou "today".
    
    Returns:
        Dict com: ticker, dates, open, high, low, close, volume.
        Dados ordenados do mais antigo ao mais recente.
        Inclui campo "error" se nenhum dado encontrado.
    """
    days = days or THRESHOLDS["history_days"]
    logger.debug(f"[Tool] fetch_price_history({ticker}) solicitou {days} dias finalizando em {target_date or 'hoje'}...")

    if target_date and target_date != "today":
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            end_date = target_dt + timedelta(days=1)
        except ValueError:
            end_date = datetime.now()
    else:
        end_date = datetime.now()

    start_date = end_date - timedelta(days=days + 15)  # margem maior p/ feriados/fds

    try:
        hist = yf.Ticker(ticker).history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        logger.debug(f"[Tool] Erro em fetch_price_history({ticker}): {e}")
        return _empty_result(ticker, error=str(e))

    if hist.empty:
        logger.debug(f"[Tool] fetch_price_history({ticker}) não obteve dados.")
        return _empty_result(ticker)

    hist = hist.tail(days)
    logger.debug(f"[Tool] fetch_price_history({ticker}) retornou {len(hist)} dias de pregão.")

    return {
        "ticker": ticker,
        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
        "open": hist["Open"].round(2).tolist(),
        "high": hist["High"].round(2).tolist(),
        "low": hist["Low"].round(2).tolist(),
        "close": hist["Close"].round(2).tolist(),
        "volume": hist["Volume"].astype(int).tolist(),
    }


@functools.lru_cache(maxsize=32)
def fetch_ticker_news(ticker: str, max_results: int = 5) -> list[dict]:
    """Busca notícias recentes de um ticker via Yahoo Finance.

    Args:
        ticker: Símbolo do ativo
        max_results: Máximo de notícias a retornar

    Returns:
        Lista de dicts com: title, publisher, link, publish_time
    """
    logger.debug(f"[Tool] fetch_ticker_news({ticker}) iniciada...")
    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception as e:
        logger.debug(f"[Tool] Erro em fetch_ticker_news({ticker}): {e}")
        return []

    processed_news = [
        {
            "title": _extract_title(item),
            "publisher": _extract_publisher(item),
            "link": _extract_link(item),
            "publish_time": _extract_pub_date(item),
        }
        for item in raw_news[:max_results]
    ]
    
    logger.debug(f"[Tool] fetch_ticker_news({ticker}) retornou {len(processed_news)} notícias.")
    return processed_news


def compute_statistical_metrics(
    stock_data: dict,
    index_data: dict,
    sector_data: dict,
    target_date: str,
) -> dict:
    """Calcula métricas estatísticas a partir dos dados OHLCV.

    Métricas:
    - Variação percentual do dia (ativo, índice, setor)
    - Volume ratio (dia / média 20 dias)
    - Tendência de mercado (SMA20 vs SMA50 do índice)
    - Flag de anomalia de volume
    """
    logger.debug("[Tool] compute_statistical_metrics agregando dados...")
    price_change = _pct_change_on_date(stock_data, target_date)
    index_change = _pct_change_on_date(index_data, target_date)
    sector_change = _pct_change_on_date(sector_data, target_date)
    volume_ratio = _volume_ratio(stock_data, target_date)
    trend = _market_trend(index_data)

    return {
        "price_change_pct": price_change,
        "index_change_pct": index_change,
        "sector_change_pct": sector_change,
        "volume_ratio": volume_ratio,
        "volume_anomaly": volume_ratio > THRESHOLDS["volume_anomaly"],
        "market_trend": trend,
    }


def _empty_result(ticker: str, error: str | None = None) -> dict:
    """Retorna um dict OHLCV vazio para um ticker."""
    result = {
        "ticker": ticker,
        "dates": [], "open": [], "high": [], "low": [], "close": [], "volume": [],
    }
    if error:
        result["error"] = error
    else:
        result["error"] = f"Nenhum dado encontrado para {ticker}"
    return result


def _extract_title(item: dict) -> str:
    content = item.get("content", {})
    return content.get("title", item.get("title", "Sem título"))


def _extract_publisher(item: dict) -> str:
    content = item.get("content", {})
    return content.get("provider", {}).get("displayName", "Desconhecido")


def _extract_link(item: dict) -> str:
    content = item.get("content", {})
    return content.get("canonicalUrl", {}).get("url", "")


def _extract_pub_date(item: dict) -> str:
    content = item.get("content", {})
    return content.get("pubDate", "")


def _pct_change_on_date(data: dict, date_str: str) -> float:
    """Calcula variação % do preço de fechamento no dia."""
    dates = data.get("dates", [])
    closes = data.get("close", [])

    idx = dates.index(date_str) if date_str in dates else (len(closes) - 1 if closes else -1)

    if idx > 0 and closes[idx - 1] != 0:
        return float(round(((closes[idx] - closes[idx - 1]) / closes[idx - 1]) * 100, 2))

    return 0.0


def _volume_ratio(data: dict, date_str: str) -> float:
    """Calcula volume_dia / média_volume_20d."""
    dates = data.get("dates", [])
    volumes = data.get("volume", [])

    idx = dates.index(date_str) if date_str in dates else (len(volumes) - 1 if volumes else -1)
    if idx < 0:
        return 1.0

    start = max(0, idx - 20)
    avg_vol = pd.Series(volumes[start:idx]).mean()
    return float(round(volumes[idx] / avg_vol, 2)) if avg_vol and avg_vol > 0 else 1.0


def _market_trend(data: dict) -> str:
    """Determina tendência via SMA20 vs SMA50 do índice."""
    closes = data.get("close", [])
    if len(closes) < THRESHOLDS["sma_long"]:
        return "sideways"

    series = pd.Series(closes)
    sma_short = float(series.rolling(THRESHOLDS["sma_short"]).mean().iloc[-1])
    sma_long = float(series.rolling(THRESHOLDS["sma_long"]).mean().iloc[-1])

    if sma_short > sma_long * 1.005:
        return "uptrend"
    if sma_short < sma_long * 0.995:
        return "downtrend"
    return "sideways"
