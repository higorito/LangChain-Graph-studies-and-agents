from rich.pretty import pprint
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from typing import Annotated, Sequence
from rich.markdown import Markdown

llm = init_chat_model("gpt-oss:20b-cloud", model_provider="ollama")
# llm = init_chat_model("ollama:qwen3-vl:4b")

@tool
def multiply(x: float, y: float) -> float:
    """Multiply x and y and return the result

    Args:
        x (float): The first number
        y (float): The second number

    Returns:
        float: The product of x and y
    """
    return x * y

messages: list[BaseMessage] = []

system_message = SystemMessage("You are a helpful assistant, and you are didactic. You have access to tools. Use them wisely. First look at the tools and then answer solve the problem")
human_message = HumanMessage("oi, sou o Higor. Quanto é 3.99 vezes 5?")

messages.append(system_message)
messages.append(human_message)

# response = llm.invoke(messages) # sem tools

tools: list[BaseTool] = [multiply]

tools_map = {t.name: t for t in tools}

llm_with_tools = llm.bind_tools(tools)
llm_response = llm_with_tools.invoke(messages)

# pprint(llm_response) #tool_calls=[{'name': 'multiply', 'args': {'x': 3.99, 'y': 5}, 'id': '51236f77-e567-4f03-9e92-703bef340045', 'type': 'tool_call'}],
# print(Markdown("---"))

messages.append(llm_response)

if isinstance(llm_response, AIMessage) and llm_response.tool_calls:
    # for tool_call in tool_calls:
    #     selected_tool = tools_map[tool_call["name"]]
    #     result = selected_tool.invoke(tool_call["args"])
    #     messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    tool_calls = llm_response.tool_calls[-1]
    name, args, id_tool_call = tool_calls["name"], tool_calls["args"], tool_calls["id"]

    try:
        selected_tool = tools_map[name]
        result = selected_tool.invoke(args)
        messages.append(ToolMessage(content=str(result), tool_call_id=id_tool_call, status="success"))
    except (KeyError, IndexError, ValueError) as e:
        messages.append(ToolMessage(content=f"Tool {name} not found", tool_call_id=id_tool_call, status="error"))

    llm_response = llm_with_tools.invoke(messages)
    messages.append(llm_response)

pprint(messages)
