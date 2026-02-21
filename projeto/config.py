from projeto.agent_base import DEFAULT_MODELS, list_providers

LLM_MODEL = DEFAULT_MODELS["openrouter"]
LLM_PROVIDER = "openrouter"
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


def normalize_company_name(name: str) -> str:
    return name.strip().lower()


def resolve_ticker(input_name: str) -> str:
    normalized = normalize_company_name(input_name)
    if "." in input_name or input_name.upper() in TICKER_SECTOR_MAP:
        return input_name.upper()
    if normalized in COMPANY_NAME_TO_TICKER:
        return COMPANY_NAME_TO_TICKER[normalized]
    return input_name.upper()


def ensure_yahoo_ticker(ticker: str) -> str:
    """Garante ticker no formato que o Yahoo Finance aceita (ex: BBAS3 -> BBAS3.SA)."""
    t = ticker.strip().upper()
    if t in TICKER_SECTOR_MAP:
        return t
    if t.endswith(".SA"):
        return t
    if f"{t}.SA" in TICKER_SECTOR_MAP:
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
    if ticker in TICKER_SECTOR_MAP:
        return TICKER_SECTOR_MAP[ticker]
    if ticker.upper().endswith(".SA"):
        return DEFAULT_BR
    return DEFAULT_US
