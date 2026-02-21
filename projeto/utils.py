"""
Utilitários compartilhados — carregamento do LLM com sistema modular.
"""
from typing import cast, TypeVar, Optional
from langchain.chat_models import init_chat_model, BaseChatModel
from pydantic import BaseModel

from projeto.config import LLM_MODEL, LLM_PROVIDER
from projeto.providers import (
    get_provider_config,
    validate_provider,
    get_provider,
    DEFAULT_MODELS
)

def load_llm(
    model: Optional[str] = None, 
    provider: Optional[str] = None,
    config: Optional[dict] = None
) -> BaseChatModel:
    """Carrega o LLM usando o sistema modular de provedores."""
    if config and "configurable" in config:
        conf = config["configurable"]
        model = model or conf.get("model")
        provider = provider or conf.get("model_provider")

    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER

    is_valid, error_msg = validate_provider(active_provider, active_model)
    if not is_valid:
        active_model = DEFAULT_MODELS.get(active_provider, active_model)

    llm_config = get_provider_config(active_provider, active_model)

    model_name = llm_config["model"]
    model_provider = llm_config["model_provider"]
    
    chat_params: dict = {
        "temperature": llm_config.get("temperature", 0.7),
    }

    if model_provider == "google":
        chat_params["google_api_key"] = llm_config.get("google_api_key")
    elif model_provider == "openai":
        chat_params["api_key"] = llm_config.get("openai_api_key")
        chat_params["base_url"] = llm_config.get("openai_base_url")
    elif model_provider == "ollama":
        chat_params["base_url"] = llm_config.get("base_url")

    llm = cast(
        "BaseChatModel",
        init_chat_model(
            model=model_name,
            model_provider=model_provider,
            **chat_params
        ),
    )
    
    return llm


T = TypeVar('T', bound=BaseModel)

def load_structured_llm(
    schema: type[T],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    config: Optional[dict] = None
) -> BaseChatModel:
    """Carrega o LLM com structured output."""
    llm = load_llm(model=model, provider=provider, config=config)
    return llm.with_structured_output(schema)


def list_available_models(provider: Optional[str] = None) -> list[str]:
    from projeto.providers import get_models_for_provider, _PROVIDERS
    if provider:
        return get_models_for_provider(provider)
    all_models = []
    for prov_name in _PROVIDERS.keys():
        all_models.extend(get_models_for_provider(prov_name))
    return all_models


def check_provider_setup(provider: str) -> tuple[bool, str]:
    try:
        prov = get_provider(provider)
        if not prov.validate_api_key():
            return False, f"API key não configurada."
        return True, f"Provedor '{provider}' configurado corretamente"
    except ValueError as e:
        return False, str(e)
