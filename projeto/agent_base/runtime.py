from collections.abc import Iterator, Mapping
from typing import Any

from langchain_core.runnables import RunnableConfig

CONFIGURABLE_KEY = "configurable"
MODEL_KEY = "model"
PROVIDER_KEY = "model_provider"

_PROVIDER_ALIASES = {
    "google": "google_genai",
    "gemini": "google_genai",
}


def normalize_provider_name(provider: str | None) -> str | None:
    raw = (provider or "").strip().lower()
    if not raw:
        return None
    return _PROVIDER_ALIASES.get(raw, raw)


def get_configurable_values(
    config: RunnableConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not config:
        return {}

    raw_values = config.get(CONFIGURABLE_KEY)
    if not isinstance(raw_values, Mapping):
        return {}

    values = dict(raw_values)
    provider = normalize_provider_name(_as_optional_str(values.get(PROVIDER_KEY)))
    if provider:
        values[PROVIDER_KEY] = provider
    return values


def resolve_model_selection(
    config: RunnableConfig | Mapping[str, Any] | None = None,
    *,
    model: str | None = None,
    provider: str | None = None,
) -> tuple[str | None, str | None]:
    values = get_configurable_values(config)
    active_model = model or _as_optional_str(values.get(MODEL_KEY))
    active_provider = normalize_provider_name(
        provider or _as_optional_str(values.get(PROVIDER_KEY))
    )
    return active_model, active_provider


def build_runnable_config(
    *,
    model: str | None = None,
    provider: str | None = None,
    thread_id: str | None = None,
    configurable: Mapping[str, Any] | None = None,
) -> RunnableConfig | None:
    values = dict(configurable or {})

    if model:
        values[MODEL_KEY] = model

    normalized_provider = normalize_provider_name(
        provider or _as_optional_str(values.get(PROVIDER_KEY))
    )
    if normalized_provider:
        values[PROVIDER_KEY] = normalized_provider

    if thread_id:
        values["thread_id"] = thread_id

    clean_values = {key: value for key, value in values.items() if value is not None}
    if not clean_values:
        return None

    return {CONFIGURABLE_KEY: clean_values}


def stream_graph_updates(
    graph: Any,
    agent_input: Any,
    *,
    config: RunnableConfig | None = None,
) -> Iterator[tuple[str, Any]]:
    for event in graph.stream(agent_input, config=config, stream_mode="updates"):
        if not isinstance(event, Mapping):
            continue
        for node_name, node_output in event.items():
            yield str(node_name), node_output


def collect_graph_updates(
    graph: Any,
    agent_input: Any,
    *,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    final_state: dict[str, Any] = {}
    for _, node_output in stream_graph_updates(graph, agent_input, config=config):
        if isinstance(node_output, Mapping):
            final_state.update(node_output)
    return final_state


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
