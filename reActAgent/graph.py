from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, ToolMessage

from tool import TOOLS, TOOLS_MAP
from state import State
from utils import load_llm

def call_llm(state: State) -> State:
    llm = load_llm().bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: State) -> State:
    llm_response = state["messages"][-1]
    if not isinstance(llm_response, AIMessage) or not llm_response.tool_calls:
        return state

    tool_calls = llm_response.tool_calls[-1]
    name, args, id_tool_call = tool_calls["name"], tool_calls["args"], tool_calls["id"]
    try:
        selected_tool = TOOLS_MAP[name]
        result = selected_tool.invoke(args)
        tool_message = ToolMessage(content=str(result), tool_call_id=id_tool_call, status="success")
    except (KeyError, IndexError, ValueError) as e:
        tool_message = ToolMessage(content=f"Tool {name} not found", tool_call_id=id_tool_call, status="error")

    return {"messages": [tool_message]}

def router(state: State) -> Literal["tool_node", "__end__"]:
    print("router...")
    llm_response = state["messages"][-1]
    if getattr(llm_response, "tool_calls", None):
        return "tool_node"
    return "__end__"

def build_graph() -> CompiledStateGraph[State, None, State, State]:
    builder = StateGraph(State)

    builder.add_node("call_llm", call_llm)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", router, ["tool_node", END])
    builder.add_edge("tool_node", "call_llm")
    # builder.add_edge("call_llm", END)

    return builder.compile(checkpointer=InMemorySaver())