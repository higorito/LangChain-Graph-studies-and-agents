"""
Modo conversacional com StateGraph: call_llm → tools_condition → tools ou END.
Usa ToolNode e tools_condition do LangGraph (padrão moderno).
"""
import warnings
import logging
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import tools_condition
from langgraph.checkpoint.memory import MemorySaver

from projeto.config import LLM_MODEL, LLM_PROVIDER
from projeto.display import console
from projeto.agent_base import load_llm
from projeto.tools.chat_tools import analisar_acao, resolver_ticker, comparar_ativos

_llm_instance = None
_active_model = None
_active_provider = None


def _get_llm():
    return _llm_instance


def _set_llm(llm):
    global _llm_instance
    _llm_instance = llm


def _get_model_provider():
    return _active_model, _active_provider


def _set_model_provider(model, provider):
    global _active_model, _active_provider
    _active_model = model
    _active_provider = provider


CHAT_TOOLS = [analisar_acao, resolver_ticker, comparar_ativos]

SYSTEM_PROMPT = """Você é um analista financeiro sênior (Bovespa e exterior), conversando no terminal.
Seja direto e profissional. Use as ferramentas quando precisar de dados de mercado; não invente números.
Se o usuário fizer pergunta de acompanhamento sobre o mesmo ativo (ex: "e as notícias?", "qual o preço?") e o resultado da ferramenta já estiver na conversa, use esse contexto em vez de chamar a ferramenta de novo."""


def _build_chat_graph():
    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    llm = _get_llm()
    if llm is None:
        raise RuntimeError("LLM não configurado. Chamar run_interactive_mode() após load_llm.")
    llm_with_tools = llm.bind_tools(CHAT_TOOLS)
    tool_node = ToolNode(CHAT_TOOLS)

    def call_llm(state: State):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(State)
    builder.add_node("call_llm", call_llm)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", tools_condition, ["tools", END])
    builder.add_edge("tools", "call_llm")
    return builder.compile(checkpointer=MemorySaver())


def run_interactive_mode(model: str | None = None, provider: str | None = None):
    warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
    logging.getLogger("langchain_core").setLevel(logging.ERROR)
    logging.getLogger("langchain_google_genai").setLevel(logging.ERROR)

    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER
    llm = load_llm(model=active_model, provider=active_provider)
    _set_llm(llm)
    _set_model_provider(active_model, active_provider)

    app = _build_chat_graph()
    config = {"configurable": {"thread_id": "sessao_terminal_1"}}

    console.print("\n[bold green]Modo Chat[/] (sair/quit/exit para encerrar)")
    console.print("[dim]Assistente financeiro. Pode analisar ativos, comparar e resolver tickers.[/]\n")
    console.print(f"[dim]Modelo: {active_model} | Provider: {active_provider}[/]\n")

    while True:
        try:
            user_input = input("Você: ").strip()
            if user_input.lower() in ("sair", "quit", "exit", "q"):
                console.print("\n[dim]Até logo![/]")
                break
            if not user_input:
                continue

            for event in app.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                stream_mode="values",
            ):
                last = event["messages"][-1]
                if last.type == "ai":
                    if getattr(last, "tool_calls", None):
                        names = [tc["name"] for tc in last.tool_calls]
                        console.print(f"\n[dim italic]... {', '.join(names)} ...[/]")
                    elif last.content:
                        text = last.content
                        if isinstance(text, list):
                            text = "".join(
                                b.get("text", b) if isinstance(b, dict) else str(b)
                                for b in text
                            )
                        if str(text).strip():
                            console.print(f"\n[bold blue]Assistente:[/] {str(text).strip()}\n")
        except KeyboardInterrupt:
            console.print("\n[dim]Interrompido. Até logo![/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Erro:[/] {e}\n")
