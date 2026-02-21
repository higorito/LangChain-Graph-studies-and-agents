import os
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    def __init__(self, name: str):
        self.name = name
        self.api_key_env: list[str] = []

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        pass

    @abstractmethod
    def get_chat_model_kwargs(self, model: str) -> dict[str, Any]:
        """Retorna kwargs prontos para init_chat_model(model=..., model_provider=..., **kwargs)."""
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        pass

    def _get_api_key(self) -> str | None:
        for env_var in self.api_key_env:
            key = os.getenv(env_var)
            if key:
                return key
        return None


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__("ollama")
        self.api_key_env = []

    def get_supported_models(self) -> list[str]:
        return ["gpt-oss:20b-cloud", "gpt-oss:120b-cloud"]

    def get_chat_model_kwargs(self, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "model_provider": "ollama",
            "temperature": 0.7,
            "base_url": os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        }

    def validate_api_key(self) -> bool:
        return True


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__("google_genai")
        self.api_key_env = ["GOOGLE_API_KEY", "GEMINI_API_KEY"]

    def get_supported_models(self) -> list[str]:
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    def get_chat_model_kwargs(self, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "model_provider": "google_genai",
            "temperature": 0.7,
            "google_api_key": self._get_api_key(),
        }

    def validate_api_key(self) -> bool:
        key = self._get_api_key()
        return key is not None and len(key) > 0


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__("openrouter")
        self.api_key_env = ["OPEN_ROUTER_API_KEY", "OPENROUTER_API_KEY"]
        self.base_url_env = "OPENROUTER_BASE_URL"

    def get_supported_models(self) -> list[str]:
        return ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"]

    def get_chat_model_kwargs(self, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "model_provider": "openai",
            "temperature": 0.7,
            "api_key": self._get_api_key(),
            "base_url": os.getenv(self.base_url_env) or "https://openrouter.ai/api/v1",
        }

    def validate_api_key(self) -> bool:
        key = self._get_api_key()
        return key is not None and len(key) > 0


_PROVIDERS: dict[str, BaseLLMProvider] = {
    "ollama": OllamaProvider(),
    "google_genai": GeminiProvider(),
    "openrouter": OpenRouterProvider(),
}


_PROVIDER_ALIASES = {"google": "google_genai"}


def get_provider(provider_name: str) -> BaseLLMProvider:
    key = provider_name.lower().strip()
    key = _PROVIDER_ALIASES.get(key, key)
    if key not in _PROVIDERS:
        raise ValueError(f"Provedor '{provider_name}' não suportado. Disponíveis: {', '.join(_PROVIDERS.keys())}")
    return _PROVIDERS[key]


def list_providers() -> list[str]:
    return list(_PROVIDERS.keys())


def get_models_for_provider(provider_name: str) -> list[str]:
    return get_provider(provider_name).get_supported_models()


def get_chat_model_kwargs(provider_name: str, model: str) -> dict[str, Any]:
    return get_provider(provider_name).get_chat_model_kwargs(model)


def validate_provider(provider_name: str, model: str) -> tuple[bool, str]:
    try:
        provider = get_provider(provider_name)
        if not provider.validate_api_key():
            return False, f"API key não configurada para {provider_name}."
        return True, ""
    except ValueError as e:
        return False, str(e)


DEFAULT_MODELS: dict[str, str] = {
    "ollama": "gpt-oss:20b-cloud",
    "google_genai": "gemini-2.0-flash",
    "openrouter": "openai/gpt-4o-mini",
}
