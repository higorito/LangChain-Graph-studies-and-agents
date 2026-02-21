"""
Estado tipado do grafo LangGraph com schemas separados (Input/Output).

Usa padrões modernos do LangGraph:
- input_schema / output_schema no StateGraph
- Annotated com reducers para campos que acumulam dados
- Separação clara de responsabilidades entre schemas
"""
from typing import Annotated, Any

from pydantic import BaseModel, Field


class InputState(BaseModel):
    """Schema de entrada do grafo — o que o usuário fornece."""
    ticker: str = Field(
        ..., description="Ticker do ativo (ex: 'PETR4.SA', 'AAPL')"
    )
    date: str = Field(
        default="today",
        description="Data do pregão: 'YYYY-MM-DD' ou 'today'",
    )

class OutputState(BaseModel):
    """Schema de saída do grafo — o que o usuário recebe."""
    ticker: str
    date: str
    metrics: dict
    classification: dict
    explanation: str

# Estado interno completo do grafo (superset de Input + Output)

class AgentState(BaseModel):
    """Estado global do grafo. Inclui todos os campos intermediários.

    Campos preenchidos progressivamente:
    - Input:    ticker, date
    - Fetch:    stock_data, index_data, sector_data, news
    - Compute:  metrics
    - Classify: classification
    - Explain:  explanation
    """
    ticker: str = ""
    date: str = "today"

    stock_data: dict = Field(default_factory=dict)
    index_data: dict = Field(default_factory=dict)
    sector_data: dict = Field(default_factory=dict)
    news: list[dict] = Field(default_factory=list)

    metrics: dict = Field(default_factory=dict)

    classification: dict = Field(default_factory=dict)

    explanation: str = ""
