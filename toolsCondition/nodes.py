from typing import Literal
from langchain_core.runnables.config import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from toolsCondition.tool import TOOLS, TOOLS_MAP
from toolsCondition.state import State
from toolsCondition.utils import load_llm

#usando o node alto nivel do langgraph(o baixo ta ni runnableConfig) e o router tmb
tool_node = ToolNode(tools=TOOLS)

def call_llm(state: State, config: RunnableConfig) -> State:
    user_type = config.get("configurable").get("user_type")

    temperature = 1 if user_type == "plus" else 0
    model = "gpt-oss:20b-cloud" if user_type == "plus" else "qwen3-vl:4b"
    model_provider = "ollama" if user_type == "plus" else "ollama"

    llm = load_llm().bind_tools(TOOLS)
    llm_with_config = llm.with_config(config={"configurable": {"model": model, "temperature": temperature, "model_provider": model_provider}})

    response = llm_with_config.invoke(state["messages"])
    return {"messages": [response]}
