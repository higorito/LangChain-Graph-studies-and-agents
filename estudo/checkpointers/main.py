import asyncio
from langchain_core.messages import HumanMessage
from langgraph.graph.state import RunnableConfig
from checkpointers.constants import DB_DSN
from rich.pretty import pprint
from rich.markdown import Markdown

from checkpointers.checkpointer import build_checkpointer_psql
from langgraph.checkpoint.base import BaseCheckpointSaver
from checkpointers.context import Context
from checkpointers.graph import build_graph
from checkpointers.utils import async_lifespan

async def run_graph(checkpointer: BaseCheckpointSaver) -> None:
    graph = build_graph(checkpointer)
    
    context = Context(user_type="plus")

    config = RunnableConfig(
        configurable={'thread_id': 999},
    )
    input = "qual o meu nome?"
    human_message = HumanMessage(content=input)

    current_messages = [human_message]
    response = await graph.ainvoke({"messages": current_messages}, config=config, context=context)

    last_message = response["messages"][-1]

    # pprint(response)
    print(Markdown( "---"))
    pprint(last_message.content)


async def main() -> None:
    async with (async_lifespan(),
                build_checkpointer_psql(DB_DSN) as checkpointer
                ):
        await run_graph(checkpointer)

if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)