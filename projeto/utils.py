"""
Utilitários compartilhados — carregamento do LLM.

Padrões modernos:
- with_structured_output para output Pydantic validado
- configurable_fields="any" para reconfiguração dinâmica em runtime
"""
from typing import cast, TypeVar

from langchain.chat_models import init_chat_model, BaseChatModel
from pydantic import BaseModel

from projeto.config import LLM_MODEL, LLM_PROVIDER


def load_llm(model: str | None = None, provider: str | None = None) -> BaseChatModel:
    """Carrega o LLM base via init_chat_model.

    Args:
        model: Sobrescreve o modelo padrão do config.py
        provider: Sobrescreve o provedor padrão do config.py
    
    Returns:
        Instância do LLM configurado
    """
    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER
    
    llm = cast(
        "BaseChatModel",
        init_chat_model(
            model=active_model,
            model_provider=active_provider,
            configurable_fields="any",
        ),
    )
    assert hasattr(llm, "invoke")
    return llm


T = TypeVar('T', bound=BaseModel)

def load_structured_llm(schema: type[T], model: str | None = None, provider: str | None = None) -> BaseChatModel:
    """Carrega o LLM com structured output via with_structured_output.

    O LLM retorna diretamente uma instância Pydantic validada,
    eliminando parse manual de JSON.

    Args:
        schema: Classe Pydantic BaseModel para o output estruturado
        model: Sobrescreve o modelo padrão do config.py
        provider: Sobrescreve o provedor padrão do config.py

    Returns:
        LLM configurado para retornar instâncias do schema
    """
    llm = load_llm(model=model, provider=provider)
    return llm.with_structured_output(schema)
