from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from checkpointers.context import Context
from checkpointers.tool import TOOLS
from checkpointers.state import State
from checkpointers.utils import load_llm

tool_node = ToolNode(tools=TOOLS)

def call_llm(state: State, runtime: Runtime[Context]) -> State:
    user_type = runtime.context.user_type

    temperature = 1 if user_type == "plus" else 0
    model = "gpt-oss:20b-cloud" if user_type == "plus" else "qwen3-vl:4b"
    model_provider = "ollama" if user_type == "plus" else "ollama"

    llm = load_llm().bind_tools(TOOLS)
    llm_with_config = llm.with_config(config={"configurable": {
                                      "model": model, "temperature": temperature, "model_provider": model_provider}})

    response = llm_with_config.invoke(state["messages"])
    return {"messages": [response]}
