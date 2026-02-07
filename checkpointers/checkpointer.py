from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

def build_checkpointer() -> InMemorySaver:
    return InMemorySaver()
 
@asynccontextmanager
async def build_checkpointer_psql(db_dsn: str) -> AsyncGenerator[AsyncPostgresSaver]:
    async with AsyncPostgresSaver.from_conn_string(db_dsn) as checkpointer:
        await checkpointer.setup()
        yield checkpointer