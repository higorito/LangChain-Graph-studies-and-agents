from collections.abc import Sequence
from dataclasses import dataclass

from projeto.agent_base.providers import (
    DEFAULT_MODELS,
    get_models_for_provider,
    list_providers,
    validate_provider,
)
from projeto.agent_base.runtime import normalize_provider_name

INTERACTIVE_DEFAULT_PROVIDER = "google_genai"
INTERACTIVE_DEFAULT_MODEL = DEFAULT_MODELS[INTERACTIVE_DEFAULT_PROVIDER]

_PROVIDER_LABELS = {
    "google_genai": "Gemini",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
}
_PROVIDER_ORDER = ("google_genai", "openrouter", "ollama")
_MODEL_DESCRIPTIONS = {
    ("google_genai", "gemini-2.0-flash"): "Padrao do chat",
    ("google_genai", "gemini-1.5-flash"): "Mais economico",
    ("google_genai", "gemini-1.5-pro"): "Mais analitico",
    ("openrouter", "openai/gpt-4o-mini"): "Cloud rapido",
    ("openrouter", "anthropic/claude-3.5-sonnet"): "Analise profunda",
    ("openrouter", "google/gemini-2.0-flash-001"): "Gemini via OpenRouter",
    ("ollama", "gpt-oss:20b-cloud"): "Local ou prox local",
    ("ollama", "gpt-oss:120b-cloud"): "Mais pesado",
}


@dataclass(frozen=True, slots=True)
class ModelOption:
    index: int
    provider: str
    model: str
    provider_label: str
    description: str
    is_default: bool
    provider_ready: bool
    provider_message: str

    @property
    def selection_key(self) -> str:
        return f"{self.provider}:{self.model}"


def resolve_interactive_selection(
    *,
    model: str | None = None,
    provider: str | None = None,
) -> tuple[str, str]:
    active_provider = normalize_provider_name(provider)
    if active_provider is None and model:
        active_provider = _infer_provider_from_model(model)
    active_provider = active_provider or INTERACTIVE_DEFAULT_PROVIDER
    if active_provider not in DEFAULT_MODELS:
        active_provider = INTERACTIVE_DEFAULT_PROVIDER

    active_model = model or DEFAULT_MODELS.get(active_provider, INTERACTIVE_DEFAULT_MODEL)
    return active_model, active_provider


def build_model_catalog() -> list[ModelOption]:
    options: list[ModelOption] = []
    providers = _ordered_providers()

    for provider in providers:
        models = get_models_for_provider(provider)
        provider_ready, provider_message = get_provider_status(provider)
        provider_label = _PROVIDER_LABELS.get(provider, provider)

        for model in models:
            options.append(
                ModelOption(
                    index=len(options) + 1,
                    provider=provider,
                    model=model,
                    provider_label=provider_label,
                    description=_MODEL_DESCRIPTIONS.get((provider, model), ""),
                    is_default=(
                        provider == INTERACTIVE_DEFAULT_PROVIDER
                        and model == INTERACTIVE_DEFAULT_MODEL
                    ),
                    provider_ready=provider_ready,
                    provider_message=provider_message,
                )
            )

    return options


def get_provider_status(provider: str) -> tuple[bool, str]:
    default_model = DEFAULT_MODELS.get(provider, "")
    is_ready, message = validate_provider(provider, default_model)
    return is_ready, message or "OK"


def find_model_option(
    selection: str,
    options: Sequence[ModelOption],
) -> ModelOption | None:
    raw = (selection or "").strip()
    if not raw:
        return None

    if raw.isdigit():
        index = int(raw)
        return next((option for option in options if option.index == index), None)

    provider_only = normalize_provider_name(raw)
    if provider_only in DEFAULT_MODELS:
        return _find_provider_default(provider_only, options)

    if ":" in raw:
        provider_token, model_token = raw.split(":", 1)
        return _find_exact_option(
            normalize_provider_name(provider_token),
            model_token.strip(),
            options,
        )

    parts = raw.split(maxsplit=1)
    if len(parts) == 2:
        maybe_provider = normalize_provider_name(parts[0])
        if maybe_provider in DEFAULT_MODELS:
            return _find_exact_option(maybe_provider, parts[1].strip(), options)

    exact_model_matches = [
        option
        for option in options
        if option.model.lower() == raw.lower()
    ]
    if len(exact_model_matches) == 1:
        return exact_model_matches[0]

    provider_label_matches = [
        option
        for option in options
        if option.provider_label.lower() == raw.lower() and option.is_default
    ]
    if len(provider_label_matches) == 1:
        return provider_label_matches[0]

    return None


def describe_current_model(model: str, provider: str) -> str:
    provider_label = _PROVIDER_LABELS.get(provider, provider)
    return f"{provider_label} / {model}"


def _find_provider_default(
    provider: str | None,
    options: Sequence[ModelOption],
) -> ModelOption | None:
    if not provider:
        return None

    default_model = DEFAULT_MODELS.get(provider)
    if default_model:
        match = _find_exact_option(provider, default_model, options)
        if match is not None:
            return match

    return next((option for option in options if option.provider == provider), None)


def _find_exact_option(
    provider: str | None,
    model: str,
    options: Sequence[ModelOption],
) -> ModelOption | None:
    if not provider:
        return None

    model_key = (model or "").strip().lower()
    return next(
        (
            option
            for option in options
            if option.provider == provider and option.model.lower() == model_key
        ),
        None,
    )


def _ordered_providers() -> list[str]:
    available = list_providers()
    ordered = [provider for provider in _PROVIDER_ORDER if provider in available]
    remaining = [provider for provider in available if provider not in ordered]
    return ordered + remaining


def _infer_provider_from_model(model: str) -> str | None:
    model_key = (model or "").strip().lower()
    if not model_key:
        return None

    matches = [
        provider
        for provider in list_providers()
        if model_key in {candidate.lower() for candidate in get_models_for_provider(provider)}
    ]
    return matches[0] if len(matches) == 1 else None
