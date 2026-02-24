"""
Schemas Pydantic para a saida estruturada do LLM.

AgentOutput e usado para garantir retorno validado automaticamente.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AgentOutput(BaseModel):
    """Saida estruturada final do agente."""

    price_change_pct: float = Field(
        ..., description="Variacao percentual do preco do ativo no dia"
    )
    index_change_pct: float = Field(
        ..., description="Variacao percentual do indice de referencia no dia"
    )
    sector_change_pct: float = Field(
        ..., description="Variacao percentual do ETF setorial no dia"
    )
    market_trend: Literal["uptrend", "downtrend", "sideways"] = Field(
        ..., description="Tendencia de mercado baseada em SMA20 vs SMA50 do indice"
    )
    volume_anomaly: bool = Field(
        ..., description="True se volume do dia > 1.8x a media de 20 dias"
    )
    movement_type: Literal["macro", "setorial", "company_specific", "technical_flow"] = Field(
        ..., description="Classificacao do tipo de movimento (canonico: setorial)"
    )
    primary_hypothesis: str = Field(
        ..., description="Hipotese principal para o movimento"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Nivel de confianca na classificacao"
    )
    explanation: str = Field(
        ..., description="Explicacao textual detalhada do movimento em portugues brasileiro"
    )

    @field_validator("movement_type", mode="before")
    @classmethod
    def _normalize_movement_type(cls, value: str) -> str:
        raw = str(value).strip().lower()
        if raw == "sectorial":
            return "setorial"
        return raw
