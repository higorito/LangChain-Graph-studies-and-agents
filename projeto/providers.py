"""
Módulo de provedores LLM modular — suporta Ollama, Google Gemini e OpenRouter
"""
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Classe base abstrata para provedores LLM."""

    def __init__(self, name: str):
        self.name = name
        self.api_key_env: List[str] = []

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Retorna lista de modelos suportados por este provedor."""
        pass

    @abstractmethod
    def get_model_config(self, model: str) -> Dict[str, Any]:
        """Retorna configuração específica do modelo."""
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """Valida se a API key está configurada corretamente."""
        pass

    def _get_api_key(self) -> Optional[str]:
        """Tenta obter a API key de uma das variáveis de ambiente suportadas."""
        for env_var in self.api_key_env:
            key = os.getenv(env_var)
            if key:
                return key
        return None


class OllamaProvider(BaseLLMProvider):
    """Provedor Ollama (local)."""

    def __init__(self):
        super().__init__("ollama")
        self.api_key_env = []

    def get_supported_models(self) -> List[str]:
        return ["gpt-oss:20b-cloud", "gpt-oss:120b-cloud"]

    def get_model_config(self, model: str) -> Dict[str, Any]:
        return {
            "model": model,
            "model_provider": "ollama",
            "temperature": 0.7,
            "base_url": os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        }

    def validate_api_key(self) -> bool:
        return True


class GeminiProvider(BaseLLMProvider):
    """Provedor Google Gemini."""

    def __init__(self):
        super().__init__("google_genai")
        self.api_key_env = ["GOOGLE_API_KEY", "GEMINI_API_KEY"]

    def get_supported_models(self) -> List[str]:
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    def get_model_config(self, model: str) -> Dict[str, Any]:
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
    """Provedor OpenRouter."""

    def __init__(self):
        super().__init__("openrouter")
        self.api_key_env = ["OPEN_ROUTER_API_KEY", "OPENROUTER_API_KEY"]
        self.base_url_env = "OPENROUTER_BASE_URL"

    def get_supported_models(self) -> List[str]:
        return ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"]

    def get_model_config(self, model: str) -> Dict[str, Any]:
        return {
            "model": model,
            "model_provider": "openai",
            "temperature": 0.7,
            "openai_api_key": self._get_api_key(),
            "openai_base_url": os.getenv(self.base_url_env) or "https://openrouter.ai/api/v1",
        }

    def validate_api_key(self) -> bool:
        key = self._get_api_key()
        return key is not None and len(key) > 0


_PROVIDERS: Dict[str, BaseLLMProvider] = {
    "ollama": OllamaProvider(),
    "google": GeminiProvider(),
    "openrouter": OpenRouterProvider(),
}


def get_provider(provider_name: str) -> BaseLLMProvider:
    provider_name = provider_name.lower()
    if provider_name not in _PROVIDERS:
        raise ValueError(f"Provedor '{provider_name}' não suportado. Disponíveis: {', '.join(_PROVIDERS.keys())}")
    return _PROVIDERS[provider_name]


def list_providers() -> List[str]:
    return list(_PROVIDERS.keys())


def validate_provider(provider_name: str, model: str) -> tuple[bool, str]:
    try:
        provider = get_provider(provider_name)
        if not provider.validate_api_key():
            return False, f"API key não configurada para {provider_name}."
        return True, ""
    except ValueError as e:
        return False, str(e)


def get_provider_config(provider_name: str, model: str) -> Dict[str, Any]:
    provider = get_provider(provider_name)
    return provider.get_model_config(model)


DEFAULT_MODELS = {
    "ollama": "gpt-oss:20b-cloud",
    "google_genai": "gemini-2.0-flash",
    "openrouter": "openai/gpt-4o-mini",
}
