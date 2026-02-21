from projeto.agent_base import load_llm, load_structured_llm, get_provider, get_models_for_provider

__all__ = ["load_llm", "load_structured_llm", "list_available_models", "check_provider_setup"]


def list_available_models(provider: str | None = None) -> list[str]:
    if provider:
        return get_models_for_provider(provider)
    from projeto.agent_base import list_providers
    all_models = []
    for prov_name in list_providers():
        all_models.extend(get_models_for_provider(prov_name))
    return all_models


def check_provider_setup(provider: str) -> tuple[bool, str]:
    try:
        prov = get_provider(provider)
        if not prov.validate_api_key():
            return False, "API key não configurada."
        return True, f"Provedor '{provider}' configurado corretamente"
    except ValueError as e:
        return False, str(e)
