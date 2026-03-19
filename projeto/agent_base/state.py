from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseInputState(BaseModel):
    """Schema base de entrada do grafo. Estenda e adicione campos (ex: ticker, date)."""
    model_config = ConfigDict(extra="forbid")


class BaseOutputState(BaseModel):
    """Schema base de saída do grafo. Estenda com os campos que o agente retorna."""
    model_config = ConfigDict(extra="forbid")


class BaseAgentState(BaseModel):
    """Estado interno base do grafo. Estenda com campos intermediários (fetch, metrics, etc.)."""
    model_config = ConfigDict(extra="allow")

    def as_output(self) -> dict[str, Any]:
        """Retorna apenas os campos que compõem a saída do agente. Sobrescreva nas subclasses."""
        return self.model_dump()
