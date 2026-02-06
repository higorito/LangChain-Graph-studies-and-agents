from langgraph.checkpoint.memory import InMemorySaver

from contextManagers.utils import Connection

def build_checkpointer(conn: Connection) -> InMemorySaver: #aqui dentro tem outros tipos de checkpointers
    conn.open_connection()
    conn.execute_query()
    return InMemorySaver()