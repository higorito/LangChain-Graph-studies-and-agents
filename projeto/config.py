import os
import re
import unicodedata
import functools
import json
from difflib import get_close_matches
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from projeto.agent_base.providers import DEFAULT_MODELS, list_providers


def _normalize_provider_name(provider: str) -> str:
    normalized = (provider or "").strip().lower()
    aliases = {
        "google": "google_genai",
        "gemini": "google_genai",
    }
    return aliases.get(normalized, normalized)


_DEFAULT_PROVIDER = _normalize_provider_name(os.getenv("LLM_PROVIDER", "ollama"))
if _DEFAULT_PROVIDER not in DEFAULT_MODELS:
    _DEFAULT_PROVIDER = "ollama"

LLM_PROVIDER = _DEFAULT_PROVIDER
LLM_MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS[LLM_PROVIDER]
AVAILABLE_PROVIDERS = list_providers()

THRESHOLDS = {
    "systemic_delta": 1.5,
    "sector_delta": 1.5,
    "volume_anomaly": 1.8,
    "sma_short": 20,
    "sma_long": 50,
    "history_days": 60,
}

TICKER_SECTOR_MAP: dict[str, dict[str, str]] = {
    "PETR4.SA": {"index": "^BVSP", "sector_etf": "XLE"},
    "PETR3.SA": {"index": "^BVSP", "sector_etf": "XLE"},
    "VALE3.SA": {"index": "^BVSP", "sector_etf": "XLB"},
    "ITUB4.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "BBDC4.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "BBAS3.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "SANB11.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "WEGE3.SA": {"index": "^BVSP", "sector_etf": "XLI"},
    "RENT3.SA": {"index": "^BVSP", "sector_etf": "XLY"},
    "MGLU3.SA": {"index": "^BVSP", "sector_etf": "XLY"},
    "ABEV3.SA": {"index": "^BVSP", "sector_etf": "XLP"},
    "SUZB3.SA": {"index": "^BVSP", "sector_etf": "XLB"},
    "JBSS3.SA": {"index": "^BVSP", "sector_etf": "XLP"},
    "VIVT3.SA": {"index": "^BVSP", "sector_etf": "XLC"},
    "TIMS3.SA": {"index": "^BVSP", "sector_etf": "XLC"},
    "ITSA4.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "AAPL": {"index": "^GSPC", "sector_etf": "XLK"},
    "MSFT": {"index": "^GSPC", "sector_etf": "XLK"},
    "GOOGL": {"index": "^GSPC", "sector_etf": "XLC"},
    "AMZN": {"index": "^GSPC", "sector_etf": "XLY"},
    "TSLA": {"index": "^GSPC", "sector_etf": "XLY"},
    "JPM": {"index": "^GSPC", "sector_etf": "XLF"},
    "NVDA": {"index": "^GSPC", "sector_etf": "XLK"},
    "META": {"index": "^GSPC", "sector_etf": "XLC"},
    "XOM": {"index": "^GSPC", "sector_etf": "XLE"},
}

DEFAULT_BR = {"index": "^BVSP", "sector_etf": "SPY"}
DEFAULT_US = {"index": "^GSPC", "sector_etf": "SPY"}

COMPANY_NAME_TO_TICKER: dict[str, str] = {
    "petrobras": "PETR4.SA",
    "petrobras preferred": "PETR4.SA",
    "petrobras ordinária": "PETR3.SA",
    "vale": "VALE3.SA",
    "itau": "ITUB4.SA",
    "itau unibanco": "ITUB4.SA",
    "bradesco": "BBDC4.SA",
    "bb": "BBAS3.SA",
    "banco do brasil": "BBAS3.SA",
    "itausa": "ITSA4.SA",
    "itau sa": "ITSA4.SA",
    "itausa investimentos": "ITSA4.SA",
    "santander": "SANB11.SA",
    "weg": "WEGE3.SA",
    "localiza": "RENT3.SA",
    "magalu": "MGLU3.SA",
    "magazine luiza": "MGLU3.SA",
    "ambev": "ABEV3.SA",
    "suzano": "SUZB3.SA",
    "jbs": "JBSS3.SA",
    "vivara": "VIVT3.SA",
    "tim": "TIMS3.SA",
    "nvidia": "NVDA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "meta": "META",
    "facebook": "META",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "exxon": "XOM",
    "exxonmobil": "XOM",
}


TICKER_ALIASES: dict[str, str] = {}
for _ticker in TICKER_SECTOR_MAP:
    TICKER_ALIASES[_ticker] = _ticker
    if _ticker.endswith(".SA"):
        TICKER_ALIASES[_ticker[:-3]] = _ticker


def normalize_company_name(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", plain).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def _normalize_search_query(name: str) -> str:
    normalized = normalize_company_name(name)
    if not normalized:
        return normalized
    legal_suffixes = {
        "sa", "s", "a", "inc", "corp", "co", "ltd", "plc", "adr", "holdings", "holding",
    }
    tokens = [t for t in normalized.split() if t not in legal_suffixes]
    compact = " ".join(tokens).strip()
    return compact or normalized


def _looks_like_b3_ticker(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{4}[0-9]{1,2}", value))


def _sanitize_symbol(value: str) -> str:
    raw = str(value or "").strip().upper().replace("$", "")
    return re.sub(r"[^A-Z0-9.\-^]", "", raw)


@functools.lru_cache(maxsize=128)
def _search_yahoo_quotes(query: str) -> tuple[dict, ...]:
    if not query:
        return ()
    url = (
        "https://query2.finance.yahoo.com/v1/finance/search"
        f"?q={quote_plus(query)}&quotesCount=12&newsCount=0"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return ()
    quotes = payload.get("quotes") or []
    return tuple(q for q in quotes if isinstance(q, dict))


@functools.lru_cache(maxsize=256)
def ticker_has_market_data(ticker: str) -> bool:
    symbol = ensure_yahoo_ticker(_sanitize_symbol(ticker))
    if not symbol:
        return False

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(symbol)}?range=5d&interval=1d"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return False

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        return False

    first = result[0] if isinstance(result[0], dict) else {}
    timestamps = first.get("timestamp") or []
    quote_list = ((first.get("indicators") or {}).get("quote") or [])
    quote_data = quote_list[0] if quote_list and isinstance(quote_list[0], dict) else {}
    closes = quote_data.get("close") or []
    valid_closes = [c for c in closes if c is not None]
    return bool(timestamps and valid_closes)


def _pick_first_live_symbol(candidates: list[str]) -> str | None:
    seen: set[str] = set()
    for candidate in candidates:
        normalized = ensure_yahoo_ticker(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if ticker_has_market_data(normalized):
            return normalized
    return None


def _score_yahoo_candidate(original: str, normalized: str, quote: dict) -> int:
    symbol = _sanitize_symbol(quote.get("symbol", ""))
    if not symbol:
        return -1

    score = 0
    original_up = _sanitize_symbol(original)
    shortname = normalize_company_name(str(quote.get("shortname", "")))
    longname = normalize_company_name(str(quote.get("longname", "")))
    display_name = f"{shortname} {longname}".strip()
    quote_type = str(quote.get("quoteType", "")).upper()
    exchange = str(quote.get("exchange", "")).upper()

    if symbol == original_up:
        score += 120
    elif symbol.startswith(original_up):
        score += 50

    if normalized and normalized in display_name:
        score += 70
    if normalized and display_name.startswith(normalized):
        score += 20

    if quote_type == "EQUITY":
        score += 20
    elif quote_type == "ETF":
        score += 10

    br_exchanges = {"SAO", "B3"}
    us_exchanges = {"NYQ", "NMS", "NAS", "NCM", "NGM", "ASE", "PCX", "BTS"}
    if exchange in br_exchanges:
        score += 35
    elif exchange in us_exchanges:
        score += 25
    else:
        score -= 60

    if symbol.endswith(".SA"):
        score += 25
        if re.fullmatch(r"[A-Z]{4}[0-9]{1,2}\.SA", symbol):
            score += 10
        if symbol.endswith(("F.SA", "Q.SA")):
            score -= 15
    if quote.get("isYahooFinance"):
        score += 5

    return score


def _is_preferred_exchange(exchange: str) -> bool:
    key = (exchange or "").upper()
    preferred = {"SAO", "B3", "NYQ", "NMS", "NAS", "NCM", "NGM", "ASE", "PCX", "BTS"}
    return key in preferred


def _resolve_ticker_from_yahoo_search(input_name: str) -> str | None:
    normalized = normalize_company_name(input_name)
    search_query = _normalize_search_query(input_name)
    queries = [q for q in dict.fromkeys([search_query, normalized]) if q]

    all_candidates: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for query in queries:
        for quote in _search_yahoo_quotes(query):
            symbol = _sanitize_symbol(quote.get("symbol", ""))
            exchange = str(quote.get("exchange", "")).upper()
            key = (symbol, exchange)
            if symbol and key not in seen_pairs:
                seen_pairs.add(key)
                all_candidates.append(quote)

    if not all_candidates:
        return None

    scored: list[tuple[int, float, str]] = []
    for quote in all_candidates:
        symbol = _sanitize_symbol(quote.get("symbol", ""))
        exchange = str(quote.get("exchange", "")).upper()
        if not symbol:
            continue
        if exchange and not _is_preferred_exchange(exchange):
            continue
        score = _score_yahoo_candidate(input_name, normalized, quote)
        yahoo_score = float(quote.get("score") or 0.0)
        scored.append((score, yahoo_score, symbol))

    scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
    if not scored:
        return None

    strong_candidates = [symbol for score, _, symbol in scored if score >= 50]
    if not strong_candidates:
        return None

    live = _pick_first_live_symbol(strong_candidates[:8])
    if live:
        return live
    return ensure_yahoo_ticker(strong_candidates[0])


def resolve_ticker(input_name: str) -> str:
    raw = (input_name or "").strip()
    if not raw:
        return ""

    normalized_input = _sanitize_symbol(raw)
    initial_candidates: list[str] = []
    if normalized_input in TICKER_ALIASES:
        initial_candidates.append(TICKER_ALIASES[normalized_input])
    if "." in normalized_input:
        initial_candidates.append(normalized_input)

    normalized = normalize_company_name(input_name)
    if normalized in COMPANY_NAME_TO_TICKER:
        initial_candidates.append(COMPANY_NAME_TO_TICKER[normalized])

    compact = normalized.replace(" ", "")
    if compact in COMPANY_NAME_TO_TICKER:
        initial_candidates.append(COMPANY_NAME_TO_TICKER[compact])

    if _looks_like_b3_ticker(normalized_input):
        initial_candidates.append(f"{normalized_input}.SA")
    elif re.fullmatch(r"[A-Z]{1,10}", normalized_input):
        initial_candidates.append(normalized_input)

    live_initial = _pick_first_live_symbol(initial_candidates)
    if live_initial:
        return live_initial

    by_search = _resolve_ticker_from_yahoo_search(raw)
    if by_search:
        return by_search

    close_matches = get_close_matches(normalized, COMPANY_NAME_TO_TICKER.keys(), n=1, cutoff=0.9)
    if close_matches:
        matched = ensure_yahoo_ticker(COMPANY_NAME_TO_TICKER[close_matches[0]])
        if ticker_has_market_data(matched):
            return matched

    if initial_candidates:
        return ensure_yahoo_ticker(initial_candidates[0])
    return ensure_yahoo_ticker(normalized_input)


def ensure_yahoo_ticker(ticker: str) -> str:
    """Garante ticker no formato que o Yahoo Finance aceita (ex: BBAS3 -> BBAS3.SA)."""
    t = (ticker or "").strip().upper().replace("$", "")
    if not t:
        return t
    if t in TICKER_ALIASES:
        return TICKER_ALIASES[t]
    if t.endswith(".SA"):
        return t
    if _looks_like_b3_ticker(t):
        return f"{t}.SA"
    return t


async def resolve_ticker_with_llm(input_name: str, llm=None) -> str:
    from pydantic import BaseModel
    from projeto.agent_base import load_llm

    class TickerSuggestion(BaseModel):
        ticker: str
        exchange: str
        confidence: str

    prompt = f"""Given the company name "{input_name}", suggest the correct stock ticker symbol.
Known tickers: {', '.join(TICKER_SECTOR_MAP.keys())}
Company names we know: {', '.join(COMPANY_NAME_TO_TICKER.keys())}
If Brazilian, add ".SA" (e.g., PETR4.SA). If American, use standard ticker (e.g., AAPL).
Respond with the ticker symbol only."""

    try:
        if llm is None:
            llm = load_llm()
        structured_llm = llm.with_structured_output(TickerSuggestion)
        result = await structured_llm.ainvoke(prompt)
        return result.ticker
    except Exception:
        return input_name.upper()


def get_ticker_mapping(ticker: str) -> dict[str, str]:
    normalized = ensure_yahoo_ticker(ticker)
    if normalized in TICKER_SECTOR_MAP:
        return TICKER_SECTOR_MAP[normalized]
    if normalized.endswith(".SA"):
        return DEFAULT_BR
    return DEFAULT_US
