"""
Configurações, constantes e mapeamentos do agente de atribuição de movimento.
"""

# ── LLM ──────────────────────────────────────────────────────────────────────
from projeto.providers import DEFAULT_MODELS, list_providers

LLM_MODEL = DEFAULT_MODELS["openrouter"]  # "openai/gpt-4o-mini"
LLM_PROVIDER = "openrouter"

AVAILABLE_PROVIDERS = list_providers()

# ── Thresholds de classificação ──────────────────────────────────────────────
THRESHOLDS = {
    "systemic_delta": 1.5,      # |ativo - índice| < 1.5% movimento macro
    "sector_delta": 1.5,        # |ativo - setor| < 1.5% movimento setorial
    "volume_anomaly": 1.8,      # volume_dia / avg_volume_20d > 1.8 anomalia
    "sma_short": 20,
    "sma_long": 50,
    "history_days": 60,
}

TICKER_SECTOR_MAP: dict[str, dict[str, str]] = {
    # Brasil (B3)
    "PETR4.SA":  {"index": "^BVSP", "sector_etf": "XLE"},   # Petróleo & Gás
    "PETR3.SA":  {"index": "^BVSP", "sector_etf": "XLE"},
    "VALE3.SA":  {"index": "^BVSP", "sector_etf": "XLB"},   # Materiais Básicos
    "ITUB4.SA":  {"index": "^BVSP", "sector_etf": "XLF"},   # Financeiro
    "BBDC4.SA":  {"index": "^BVSP", "sector_etf": "XLF"},
    "BBAS3.SA":  {"index": "^BVSP", "sector_etf": "XLF"},
    "SANB11.SA": {"index": "^BVSP", "sector_etf": "XLF"},
    "WEGE3.SA":  {"index": "^BVSP", "sector_etf": "XLI"},   # Industrial
    "RENT3.SA":  {"index": "^BVSP", "sector_etf": "XLY"},   # Consumo Disc.
    "MGLU3.SA":  {"index": "^BVSP", "sector_etf": "XLY"},
    "ABEV3.SA":  {"index": "^BVSP", "sector_etf": "XLP"},   # Consumo Básico
    "SUZB3.SA":  {"index": "^BVSP", "sector_etf": "XLB"},   # Materiais
    "JBSS3.SA":  {"index": "^BVSP", "sector_etf": "XLP"},   # Consumo Básico
    "VIVT3.SA":  {"index": "^BVSP", "sector_etf": "XLC"},   # Comunicações
    # EUA
    "AAPL":  {"index": "^GSPC", "sector_etf": "XLK"},       # Tecnologia
    "MSFT":  {"index": "^GSPC", "sector_etf": "XLK"},
    "GOOGL": {"index": "^GSPC", "sector_etf": "XLC"},       # Comunicações
    "AMZN":  {"index": "^GSPC", "sector_etf": "XLY"},       # Consumo Disc.
    "TSLA":  {"index": "^GSPC", "sector_etf": "XLY"},
    "JPM":   {"index": "^GSPC", "sector_etf": "XLF"},       # Financeiro
    "NVDA":  {"index": "^GSPC", "sector_etf": "XLK"},       # Tecnologia
    "META":  {"index": "^GSPC", "sector_etf": "XLC"},       # Comunicações
    "XOM":   {"index": "^GSPC", "sector_etf": "XLE"},       # Energia
}

# Fallback inteligente
DEFAULT_BR = {"index": "^BVSP", "sector_etf": "SPY"}
DEFAULT_US = {"index": "^GSPC", "sector_etf": "SPY"}

# mudar depois
COMPANY_NAME_TO_TICKER: dict[str, str] = {
    # Brasil
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
    # EUA
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
    "petrobras": "PETR4.SA",
}


def normalize_company_name(name: str) -> str:
    """Normaliza o nome da empresa para busca no mapeamento."""
    return name.strip().lower()


def resolve_ticker(input_name: str) -> str:
    """Resolve nome de empresa ou ticker para ticker válido.
    
    Se o input já for um ticker válido (contém letras), retorna ele mesmo.
    Se for um nome de empresa, faz o lookup no mapeamento.
    """
    normalized = normalize_company_name(input_name)
    
    if "." in input_name or input_name.upper() in TICKER_SECTOR_MAP:
        return input_name.upper()
    
    if normalized in COMPANY_NAME_TO_TICKER:
        return COMPANY_NAME_TO_TICKER[normalized]
    
    return input_name.upper()


async def resolve_ticker_with_llm(input_name: str, llm=None) -> str:
    """Resolve ticker usando LLM como fallback."""
    from pydantic import BaseModel
    
    class TickerSuggestion(BaseModel):
        ticker: str
        exchange: str
        confidence: str
    
    prompt = f"""Given the company name "{input_name}", suggest the correct stock ticker symbol.
    
Known tickers in our system: {', '.join(TICKER_SECTOR_MAP.keys())}
Company names we know: {', '.join(COMPANY_NAME_TO_TICKER.keys())}

If the company is Brazilian, add ".SA" suffix (e.g., PETR4.SA).
If American, use the standard ticker (e.g., AAPL, MSFT).

Respond with the ticker symbol only, nothing else."""

    try:
        if llm is None:
            from projeto.utils import load_llm
            llm = load_llm()
            
        structured_llm = llm.with_structured_output(TickerSuggestion)
        result = await structured_llm.ainvoke(prompt)
        return result.ticker
    except Exception:
        return input_name.upper()


def get_ticker_mapping(ticker: str) -> dict[str, str]:
    """Retorna o mapeamento de índice e ETF setorial para um ticker.
    
    Se o ticker não estiver no mapa, usa fallback baseado no sufixo .SA.
    """
    if ticker in TICKER_SECTOR_MAP:
        return TICKER_SECTOR_MAP[ticker]
    
    # Fallback: .SA -> Brasil, senão -> EUA
    if ticker.upper().endswith(".SA"):
        return DEFAULT_BR
    return DEFAULT_US
