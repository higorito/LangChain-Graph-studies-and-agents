from langchain_core.messages import HumanMessage
from langgraph.graph.state import RunnableConfig
from rich.pretty import pprint
from rich.markdown import Markdown

from contextManagers.checkpointer import build_checkpointer
from contextManagers.context import Context
from contextManagers.graph import build_graph
from contextManagers.utils import Connection, sync_lifespan

def main(connection: Connection) -> None:
    checkpointer =  build_checkpointer(connection)
    graph = build_graph(checkpointer)
    
    context = Context(user_type="plus")

    config = RunnableConfig(
        configurable={'thread_id': 999},
    )
    input = "faça 44 vezes 33"
    human_message = HumanMessage(content=input)

    current_messages = [human_message]
    response = graph.invoke({"messages": current_messages}, config=config, context=context)
    
    last_message = response["messages"][-1]

    # pprint(response)
    print(Markdown( "---"))
    pprint(last_message.content)

if __name__ == "__main__":
    with sync_lifespan() as connection:
        main(connection)