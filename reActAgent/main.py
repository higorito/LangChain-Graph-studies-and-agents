from langchain_core.messages import HumanMessage
from langgraph.graph.state import RunnableConfig
from rich.pretty import pprint
from rich.markdown import Markdown

from reActAgent.graph import build_graph

def main() -> None:
    config = RunnableConfig(configurable={'thread_id': 999})
    graph = build_graph()

    input = "Ola, quanto é 5 dividido por 2 pega o resultado e multiplica por 3.14?"
    human_message = HumanMessage(content=input)

    current_messages = [human_message]
    response = graph.invoke({"messages": current_messages}, config=config)

    pprint(response)
    print(Markdown( "---"))
    pprint(response["messages"][-1].content)

if __name__ == "__main__":
    main()