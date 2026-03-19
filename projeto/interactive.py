import logging
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from projeto.agent_base.checkpoint import (
    get_checkpoint_backend_status,
    get_checkpointer,
    get_checkpointer_cm,
    resolve_checkpoint_target,
)
from projeto.agent_base.runtime import build_runnable_config
from projeto.interactive_llm import (
    configure_runtime,
    get_active_llm,
    get_active_model_provider,
    get_bound_chat_llm,
)
from projeto.interactive_models import (
    find_model_option,
    get_provider_status,
    resolve_interactive_selection,
)
from projeto.interactive_terminal import InteractiveTerminal, SlashCommand, parse_command

EXIT_COMMANDS = {"exit", "quit", "q"}
SYSTEM_PROMPT = """Voce e um analista financeiro senior para Bovespa e exterior.
Responda em portugues brasileiro com formato limpo em markdown.
Comece pela conclusao, depois detalhe os drivers em bullets curtos.
Use as ferramentas quando precisar de dados de mercado e nao invente numeros.
Quando o usuario pedir comparacao entre dois ativos, use comparar_ativos uma unica vez.
Nao chame analisar_acao duas vezes para perguntas comparativas.
Se houver incerteza, diga isso explicitamente.
Se o usuario fizer perguntas de acompanhamento sobre o mesmo ativo e o contexto ja estiver na conversa, reutilize esse contexto antes de chamar ferramentas novamente."""


@dataclass(slots=True)
class ChatSession:
    checkpointer: Any
    app: Any | None = None

    def get_app(self) -> Any:
        if self.app is None:
            self.app = _build_chat_graph(self.checkpointer)
        return self.app


def _get_llm():
    return get_active_llm()


def _get_model_provider():
    return get_active_model_provider()


def _get_chat_tools() -> list[Any]:
    from projeto.tools.chat_tools import analisar_acao, comparar_ativos, resolver_ticker

    return [comparar_ativos, analisar_acao, resolver_ticker]


def _build_chat_graph(checkpointer):
    from typing import Annotated, Sequence, TypedDict

    from langchain_core.messages import BaseMessage, SystemMessage
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
    from langgraph.prebuilt.tool_node import tools_condition

    chat_tools = _get_chat_tools()

    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    tool_node = ToolNode(chat_tools)

    def call_llm(state: State):
        llm_with_tools = get_bound_chat_llm(chat_tools)
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(State)
    builder.add_node("call_llm", call_llm)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", tools_condition, ["tools", END])
    builder.add_edge("tools", "call_llm")
    return builder.compile(checkpointer=checkpointer)


def _message_to_text(content: object) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", block)))
            else:
                parts.append(str(block))
        return "".join(parts).strip()
    return str(content).strip()


def _message_signature(message: Any) -> str:
    message_id = getattr(message, "id", None)
    if message_id:
        return str(message_id)
    return f"{message.type}:{getattr(message, 'name', '')}:{_message_to_text(getattr(message, 'content', ''))}"


def _render_stream_event(event: dict, terminal: InteractiveTerminal, seen: set[str]) -> None:
    messages = event.get("messages") or []
    if not messages:
        return

    last = messages[-1]
    signature = _message_signature(last)
    if signature in seen:
        return
    seen.add(signature)

    if last.type == "ai":
        tool_calls = getattr(last, "tool_calls", None) or []
        if tool_calls:
            terminal.render_tool_calls([call["name"] for call in tool_calls])
            return

        text = _message_to_text(last.content)
        if text:
            model, provider = get_active_model_provider()
            terminal.render_assistant(
                text,
                provider=provider or "desconhecido",
                model=model or "desconhecido",
            )
        return

    if last.type == "tool":
        terminal.render_tool_result(
            name=getattr(last, "name", None),
            content=getattr(last, "content", ""),
        )


def _run_chat_turn(
    session: ChatSession,
    config: dict,
    user_input: str,
    terminal: InteractiveTerminal,
) -> None:
    from langchain_core.messages import HumanMessage

    app = session.get_app()
    seen: set[str] = set()
    for event in app.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="values",
    ):
        _render_stream_event(event, terminal, seen)


def _handle_model_command(argument: str, terminal: InteractiveTerminal) -> None:
    from projeto.interactive_models import build_model_catalog

    catalog = build_model_catalog()
    current_model, current_provider = get_active_model_provider()

    selection = argument
    if not selection:
        terminal.render_model_catalog(
            catalog,
            current_provider=current_provider,
            current_model=current_model,
        )
        selection = terminal.prompt_model_selection()
        if not selection:
            terminal.render_info("Troca de modelo cancelada.")
            return

    option = find_model_option(selection, catalog)
    if option is None:
        terminal.render_error("Modelo nao reconhecido. Use /model para abrir o catalogo.")
        return

    configure_runtime(model=option.model, provider=option.provider)
    terminal.render_model_changed(provider=option.provider, model=option.model)
    if not option.provider_ready:
        terminal.render_warning(option.provider_message)


def _handle_command(
    command: SlashCommand,
    *,
    terminal: InteractiveTerminal,
    checkpoint_label: str,
    thread_id: str,
) -> bool:
    if command.name in EXIT_COMMANDS:
        terminal.render_info("Ate logo!")
        return False

    if command.name in {"help", "h"}:
        terminal.render_help()
        return True

    if command.name in {"status", "config"}:
        model, provider = get_active_model_provider()
        terminal.render_status(
            provider=provider or "desconhecido",
            model=model or "desconhecido",
            checkpoint_label=checkpoint_label,
            thread_id=thread_id,
        )
        return True

    if command.name in {"model", "models", "provider"}:
        _handle_model_command(command.argument, terminal)
        return True

    if command.name in {"clear", "cls"}:
        terminal.clear()
        model, provider = get_active_model_provider()
        terminal.render_welcome(
            provider=provider or "desconhecido",
            model=model or "desconhecido",
            checkpoint_label=checkpoint_label,
            thread_id=thread_id,
        )
        return True

    terminal.render_error("Comando nao suportado. Use /help para ver as opcoes.")
    return True


def _run_chat_loop(
    session: ChatSession,
    config: dict,
    *,
    terminal: InteractiveTerminal,
    checkpoint_label: str,
    thread_id: str,
) -> None:
    while True:
        try:
            model, provider = get_active_model_provider()
            user_input = terminal.prompt(provider=provider, model=model)
            if user_input.lower() in EXIT_COMMANDS:
                terminal.render_info("Ate logo!")
                break
            if not user_input:
                continue

            command = parse_command(user_input)
            if command is not None:
                should_continue = _handle_command(
                    command,
                    terminal=terminal,
                    checkpoint_label=checkpoint_label,
                    thread_id=thread_id,
                )
                if not should_continue:
                    break
                continue

            _run_chat_turn(session, config, user_input, terminal)
        except KeyboardInterrupt:
            terminal.render_info("Interrompido. Ate logo!")
            break
        except Exception as error:
            _, provider = get_active_model_provider()
            provider_ready, _ = get_provider_status(provider or "")
            if not provider_ready:
                terminal.render_error(
                    "O modelo ativo nao conseguiu responder. Use /model para trocar o runtime.",
                    error,
                )
            else:
                terminal.render_error("Falha durante a conversa.", error)


@contextmanager
def _chat_app_context(
    *,
    checkpointer,
    checkpoint_backend: str,
    checkpoint_conn_string: str | None,
) -> Iterator[tuple[ChatSession, str, str | None]]:
    if checkpointer is not None:
        yield ChatSession(checkpointer), "custom", None
        return

    backend, resolved_uri = resolve_checkpoint_target(
        checkpoint_backend,
        checkpoint_conn_string,
    )

    backend_ready, backend_message = get_checkpoint_backend_status(backend)
    if not backend_ready and backend == "sqlite":
        fallback_message = (
            f"{backend_message}. O chat vai abrir em memory, sem persistencia em disco, "
            "ate o pacote de sqlite ser instalado."
        )
        yield ChatSession(get_checkpointer("memory")), "memory (fallback)", fallback_message
        return

    if backend == "memory":
        yield ChatSession(get_checkpointer("memory")), "memory", None
        return

    with get_checkpointer_cm(backend, resolved_uri) as runtime_checkpointer:
        label = f"{backend}: {resolved_uri}" if resolved_uri else backend
        yield ChatSession(runtime_checkpointer), label, None


def run_interactive_mode(
    model: str | None = None,
    provider: str | None = None,
    checkpointer=None,
    checkpoint_backend: str = "sqlite",
    checkpoint_conn_string: str | None = None,
    thread_id: str = "sessao_terminal_1",
):
    warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
    logging.getLogger("langchain_core").setLevel(logging.ERROR)
    logging.getLogger("langchain_google_genai").setLevel(logging.ERROR)

    terminal = InteractiveTerminal()
    active_model, active_provider = resolve_interactive_selection(
        model=model,
        provider=provider,
    )
    configure_runtime(model=active_model, provider=active_provider)
    run_config = build_runnable_config(thread_id=thread_id) or {}

    with _chat_app_context(
        checkpointer=checkpointer,
        checkpoint_backend=checkpoint_backend,
        checkpoint_conn_string=checkpoint_conn_string,
    ) as (session, checkpoint_label, checkpoint_warning):
        terminal.render_welcome(
            provider=active_provider,
            model=active_model,
            checkpoint_label=checkpoint_label,
            thread_id=thread_id,
        )

        if checkpoint_warning:
            terminal.render_warning(checkpoint_warning)

        provider_ready, provider_message = get_provider_status(active_provider)
        if not provider_ready:
            terminal.render_warning(
                "O provider atual nao parece configurado. "
                f"{provider_message} Use /model para trocar antes da primeira pergunta."
            )

        _run_chat_loop(
            session,
            run_config,
            terminal=terminal,
            checkpoint_label=checkpoint_label,
            thread_id=thread_id,
        )
