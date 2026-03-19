import os
from collections.abc import Mapping
from typing import Any, Optional, TypeVar, cast

from pydantic import BaseModel
from langchain.chat_models import init_chat_model, BaseChatModel
from langchain_core.runnables import RunnableConfig

from projeto.agent_base.providers import (
    get_chat_model_kwargs,
    validate_provider,
    DEFAULT_MODELS,
)
from projeto.agent_base.runtime import normalize_provider_name, resolve_model_selection


def _get_default_provider() -> str:
    provider_from_env = normalize_provider_name(os.getenv("LLM_PROVIDER") or "ollama")
    if provider_from_env not in DEFAULT_MODELS:
        return "ollama"
    return cast(str, provider_from_env)


def load_llm(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    config: RunnableConfig | Mapping[str, Any] | None = None,
) -> BaseChatModel:
    model, provider = resolve_model_selection(config, model=model, provider=provider)
    default_provider = _get_default_provider()
    active_provider = provider or default_provider
    active_model = model or DEFAULT_MODELS.get(active_provider, DEFAULT_MODELS[default_provider])

    is_valid, _ = validate_provider(active_provider, active_model)
    if not is_valid:
        active_provider = active_provider if active_provider in DEFAULT_MODELS else default_provider
        active_model = DEFAULT_MODELS.get(active_provider, DEFAULT_MODELS[default_provider])

    kwargs = get_chat_model_kwargs(active_provider, active_model)
    return cast(
        BaseChatModel,
        init_chat_model(**kwargs),
    )


T = TypeVar("T", bound=BaseModel)


def load_structured_llm(
    schema: type[T],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    config: RunnableConfig | Mapping[str, Any] | None = None,
) -> BaseChatModel:
    llm = load_llm(model=model, provider=provider, config=config)
    return llm.with_structured_output(schema)

