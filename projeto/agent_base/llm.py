from typing import cast, TypeVar, Optional
from pydantic import BaseModel
from langchain.chat_models import init_chat_model, BaseChatModel

from projeto.agent_base.providers import (
    get_chat_model_kwargs,
    validate_provider,
    DEFAULT_MODELS,
)


def load_llm(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    config: Optional[dict] = None,
) -> BaseChatModel:
    if config and "configurable" in config:
        conf = config["configurable"]
        model = model or conf.get("model")
        provider = provider or conf.get("model_provider")

    _default_provider = "ollama"
    active_provider = provider or _default_provider
    active_model = model or DEFAULT_MODELS.get(active_provider, DEFAULT_MODELS[_default_provider])

    is_valid, _ = validate_provider(active_provider, active_model)
    if not is_valid:
        active_model = DEFAULT_MODELS.get(active_provider, active_model)

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
    config: Optional[dict] = None,
) -> BaseChatModel:
    llm = load_llm(model=model, provider=provider, config=config)
    return llm.with_structured_output(schema)

