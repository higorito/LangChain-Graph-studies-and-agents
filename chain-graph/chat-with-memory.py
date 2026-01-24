from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain.chat_models import init_chat_model
from rich import print
from rich.pretty import pprint
from rich.markdown import Markdown
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import RunnableConfig

llm = init_chat_model("gpt-oss:20b-cloud", model_provider="ollama")
# llm = init_chat_model("ollama:qwen3-vl:4b")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] #cada vez que manipula messages, adiciona com add_messages, mantendo a memoria

def call_llm(state: AgentState) -> AgentState:
    llm_response = llm.invoke(state["messages"]) #vai ter o histórico de conversa
    # llm_response = AIMessage("retorno genérico do LLM")
    return {"messages": [llm_response]} #atualiza o estado, trigger no add_messages e une as mensagens

builder = StateGraph(AgentState, context_schema=None, input_schema=AgentState, output_schema=AgentState)

builder.add_node("call_llm", call_llm)

builder.add_edge(START, "call_llm")
builder.add_edge("call_llm", END)

# graph = builder.compile()

# human_message = HumanMessage(content="Oi tudo bem? sou o Higor. qual o seu nome?")
# response = graph.invoke({"messages": [human_message]})

# pprint(response["messages"][-1].content)
# print(Markdown("---"))

# human_message = HumanMessage(content="lembra do nome?")
# response = graph.invoke({"messages": [human_message]})

# pprint(response["messages"][-1].content)
# print(Markdown("---"))
# ate aqui ele tava sem memoria

checkpointer = InMemorySaver()
graph = builder.compile(
    checkpointer=checkpointer
)

config = RunnableConfig(
    configurable={
        'thread_id': 'chat_with_memory',
    }
)

while True:
    input_message = input("Digite sua mensagem: ")
    if input_message.lower() == "q":
        print("Até mais!")
        print(Markdown("---"))
        break

    human_message = HumanMessage(content=input_message)

    response = graph.invoke({"messages": [human_message]},
        config=config
    )
    print(Markdown(str(response["messages"][-1].content)))
    print(Markdown("---"))