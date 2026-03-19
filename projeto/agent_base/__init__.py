from importlib import import_module

_EXPORTS = {
    "BaseInputState": ("projeto.agent_base.state", "BaseInputState"),
    "BaseAgentState": ("projeto.agent_base.state", "BaseAgentState"),
    "BaseOutputState": ("projeto.agent_base.state", "BaseOutputState"),
    "get_provider": ("projeto.agent_base.providers", "get_provider"),
    "list_providers": ("projeto.agent_base.providers", "list_providers"),
    "get_models_for_provider": ("projeto.agent_base.providers", "get_models_for_provider"),
    "get_chat_model_kwargs": ("projeto.agent_base.providers", "get_chat_model_kwargs"),
    "validate_provider": ("projeto.agent_base.providers", "validate_provider"),
    "DEFAULT_MODELS": ("projeto.agent_base.providers", "DEFAULT_MODELS"),
    "load_llm": ("projeto.agent_base.llm", "load_llm"),
    "load_structured_llm": ("projeto.agent_base.llm", "load_structured_llm"),
    "get_checkpointer": ("projeto.agent_base.checkpoint", "get_checkpointer"),
    "get_checkpointer_cm": ("projeto.agent_base.checkpoint", "get_checkpointer_cm"),
    "get_checkpointer_memory": ("projeto.agent_base.checkpoint", "get_checkpointer_memory"),
    "GraphNodeSpec": ("projeto.agent_base.graph", "GraphNodeSpec"),
    "create_state_graph": ("projeto.agent_base.graph", "create_state_graph"),
    "add_graph_nodes": ("projeto.agent_base.graph", "add_graph_nodes"),
    "add_sequence_nodes": ("projeto.agent_base.graph", "add_sequence_nodes"),
    "build_parallel_then_sequence_graph": (
        "projeto.agent_base.graph",
        "build_parallel_then_sequence_graph",
    ),
    "build_runnable_config": ("projeto.agent_base.runtime", "build_runnable_config"),
    "get_configurable_values": ("projeto.agent_base.runtime", "get_configurable_values"),
    "resolve_model_selection": ("projeto.agent_base.runtime", "resolve_model_selection"),
    "stream_graph_updates": ("projeto.agent_base.runtime", "stream_graph_updates"),
    "collect_graph_updates": ("projeto.agent_base.runtime", "collect_graph_updates"),
    "normalize_provider_name": ("projeto.agent_base.runtime", "normalize_provider_name"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
