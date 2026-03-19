from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from projeto.interactive_models import resolve_interactive_selection


@dataclass(slots=True)
class InteractiveRuntime:
    provider: str
    model: str
    llm: Any | None = None

    def get_or_create_llm(self) -> Any:
        if self.llm is None:
            from projeto.agent_base.llm import load_llm

            self.llm = load_llm(model=self.model, provider=self.provider)
        return self.llm

    def bind_tools(self, tools: Sequence[Any]) -> Any:
        return self.get_or_create_llm().bind_tools(list(tools))


_ACTIVE_RUNTIME: InteractiveRuntime | None = None


def configure_runtime(
    *,
    model: str | None = None,
    provider: str | None = None,
) -> InteractiveRuntime:
    active_model, active_provider = resolve_interactive_selection(
        model=model,
        provider=provider,
    )
    runtime = InteractiveRuntime(
        provider=active_provider,
        model=active_model,
    )
    set_active_runtime(runtime)
    return runtime


def set_active_runtime(runtime: InteractiveRuntime) -> None:
    global _ACTIVE_RUNTIME
    _ACTIVE_RUNTIME = runtime


def get_active_runtime() -> InteractiveRuntime:
    if _ACTIVE_RUNTIME is None:
        raise RuntimeError("Runtime interativo nao configurado.")
    return _ACTIVE_RUNTIME


def get_active_llm() -> Any | None:
    runtime = _ACTIVE_RUNTIME
    if runtime is None:
        return None
    try:
        return runtime.get_or_create_llm()
    except Exception:
        return None


def get_active_model_provider() -> tuple[str | None, str | None]:
    runtime = _ACTIVE_RUNTIME
    if runtime is None:
        return None, None
    return runtime.model, runtime.provider


def get_bound_chat_llm(tools: Sequence[Any]) -> Any:
    return get_active_runtime().bind_tools(tools)
