from pydantic import Field

from projeto.agent_base.state import BaseInputState, BaseOutputState, BaseAgentState


class InputState(BaseInputState):
    ticker: str = Field(..., description="Ticker do ativo (ex: 'PETR4.SA', 'AAPL')")
    date: str = Field(default="today", description="Data do pregão: 'YYYY-MM-DD' ou 'today'")


class OutputState(BaseOutputState):
    ticker: str
    date: str
    metrics: dict
    classification: dict
    explanation: str


class AgentState(BaseAgentState):
    ticker: str = ""
    date: str = "today"
    stock_data: dict = Field(default_factory=dict)
    index_data: dict = Field(default_factory=dict)
    sector_data: dict = Field(default_factory=dict)
    news: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    classification: dict = Field(default_factory=dict)
    explanation: str = ""
