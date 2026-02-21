"""
Checkpointer genérico: memory (in-memory), sqlite ou postgres.
Usa os savers de alto nível do LangGraph (SqliteSaver, PostgresSaver quando instalados).
"""
import os
from contextlib import contextmanager, ExitStack
from typing import Iterator, Any

from langgraph.checkpoint.memory import MemorySaver

_BACKENDS = ("memory", "sqlite", "postgres")


def get_checkpointer_memory() -> MemorySaver:
    """Checkpointer em memória (padrão). Estado perdido ao encerrar o processo."""
    return MemorySaver()


@contextmanager
def get_checkpointer_cm(
    backend: str,
    conn_string: str | None = None,
) -> Iterator[Any]:
    """Context manager para qualquer backend. Para 'memory' apenas retorna o saver (sem fechar)."""
    backend = (backend or "memory").lower().strip()
    if backend not in _BACKENDS:
        raise ValueError(f"backend deve ser um de {_BACKENDS}")
    
    if backend == "memory":
        yield get_checkpointer_memory()
        return
    
    uri = conn_string
    if not uri and backend == "postgres":
        uri = os.getenv("CHECKPOINT_POSTGRES_URI")
    if not uri and backend == "sqlite":
        uri = os.getenv("CHECKPOINT_SQLITE_URI") or ":memory:"
    if backend == "postgres" and not uri:
        raise ValueError("postgres exige conn_string ou env CHECKPOINT_POSTGRES_URI")
    
    with ExitStack() as stack:
        if backend == "sqlite":
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
            except ImportError:
                raise ImportError("Para backend 'sqlite' instale: pip install langgraph-checkpoint-sqlite") from None
            saver = stack.enter_context(SqliteSaver.from_conn_string(uri or ":memory:"))
            yield saver
        elif backend == "postgres":
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
            except ImportError:
                raise ImportError("Para backend 'postgres' instale: pip install langgraph-checkpoint-postgres") from None
            saver = stack.enter_context(PostgresSaver.from_conn_string(uri))
            saver.setup()
            yield saver


def get_checkpointer(
    backend: str = "memory",
    conn_string: str | None = None,
) -> MemorySaver:
    """Retorna um checkpointer para uso direto (apenas 'memory').
    Para sqlite/postgres use get_checkpointer_cm() e rode o app dentro do `with`."""
    backend = (backend or "memory").lower().strip()
    if backend not in _BACKENDS:
        raise ValueError(f"backend deve ser um de {_BACKENDS}")
    if backend == "memory":
        return get_checkpointer_memory()
    raise ValueError(
        "Para sqlite/postgres use get_checkpointer_cm(backend, conn_string) e execute o app dentro do context manager."
    )
