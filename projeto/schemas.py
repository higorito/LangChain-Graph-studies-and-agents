"""
Schemas Pydantic para a saída estruturada do LLM.

AgentOutput é usado com `with_structured_output` para garantir que o LLM
retorne dados validados automaticamente — sem parse manual de JSON.
"""
from typing import Literal

from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    """Saída estruturada do agente — usada com with_structured_output.

    O LLM retorna diretamente uma instância validada deste model,
    eliminando a necessidade de parse manual de JSON.
    """
    price_change_pct: float = Field(
        ..., description="Variação percentual do preço do ativo no dia"
    )
    index_change_pct: float = Field(
        ..., description="Variação percentual do índice de referência no dia"
    )
    sector_change_pct: float = Field(
        ..., description="Variação percentual do ETF setorial no dia"
    )
    market_trend: Literal["uptrend", "downtrend", "sideways"] = Field(
        ..., description="Tendência de mercado baseada em SMA20 vs SMA50 do índice"
    )
    volume_anomaly: bool = Field(
        ..., description="True se volume do dia > 1.8x a média de 20 dias"
    )
    movement_type: Literal["macro", "setorial", "company_specific", "technical_flow"] = Field(
        ..., description="Classificação do tipo de movimento"
    )
    primary_hypothesis: str = Field(
        ..., description="Hipótese principal para o movimento"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Nível de confiança na classificação"
    )
    explanation: str = Field(
        ..., description="Explicação textual detalhada do movimento em português brasileiro"
    )
