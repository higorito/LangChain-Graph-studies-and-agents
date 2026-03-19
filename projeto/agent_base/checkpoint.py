"""
Checkpointer generico: memory (in-memory), sqlite ou postgres.
Usa os savers de alto nivel do LangGraph.
"""
from importlib import import_module
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator

from langgraph.checkpoint.memory import MemorySaver

_BACKENDS = ("memory", "sqlite", "postgres")
_DEFAULT_SQLITE_FILENAME = "chat_history.db"


def get_default_sqlite_checkpoint_uri() -> str:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / _DEFAULT_SQLITE_FILENAME)


def resolve_checkpoint_target(
    backend: str,
    conn_string: str | None = None,
) -> tuple[str, str | None]:
    normalized_backend = (backend or "memory").lower().strip()
    if normalized_backend not in _BACKENDS:
        raise ValueError(f"backend deve ser um de {_BACKENDS}")

    if normalized_backend == "memory":
        return normalized_backend, None

    if normalized_backend == "postgres":
        uri = conn_string or os.getenv("CHECKPOINT_POSTGRES_URI")
        if not uri:
            raise ValueError("postgres exige conn_string ou env CHECKPOINT_POSTGRES_URI")
        return normalized_backend, uri

    uri = conn_string or os.getenv("CHECKPOINT_SQLITE_URI") or get_default_sqlite_checkpoint_uri()
    return normalized_backend, uri


def get_checkpoint_backend_status(backend: str) -> tuple[bool, str]:
    normalized_backend = (backend or "memory").lower().strip()
    if normalized_backend not in _BACKENDS:
        return False, f"backend deve ser um de {_BACKENDS}"

    if normalized_backend == "memory":
        return True, "memory disponivel"

    module_name = {
        "sqlite": "langgraph.checkpoint.sqlite",
        "postgres": "langgraph.checkpoint.postgres",
    }[normalized_backend]
    install_hint = {
        "sqlite": "pip install langgraph-checkpoint-sqlite",
        "postgres": "pip install langgraph-checkpoint-postgres",
    }[normalized_backend]

    try:
        import_module(module_name)
    except ImportError:
        return False, f"{normalized_backend} indisponivel neste ambiente. Instale com: {install_hint}"

    return True, f"{normalized_backend} disponivel"


def get_checkpointer_memory() -> MemorySaver:
    """Checkpointer em memoria. Estado perdido ao encerrar o processo."""
    return MemorySaver()


@contextmanager
def get_checkpointer_cm(
    backend: str,
    conn_string: str | None = None,
) -> Iterator[Any]:
    """Context manager para qualquer backend. Para memory apenas retorna o saver."""
    resolved_backend, uri = resolve_checkpoint_target(backend, conn_string)

    if resolved_backend == "memory":
        yield get_checkpointer_memory()
        return

    with ExitStack() as stack:
        if resolved_backend == "sqlite":
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
            except ImportError:
                raise ImportError(
                    "Para backend 'sqlite' instale: pip install langgraph-checkpoint-sqlite"
                ) from None
            saver = stack.enter_context(SqliteSaver.from_conn_string(uri or ":memory:"))
            yield saver
            return

        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            raise ImportError(
                "Para backend 'postgres' instale: pip install langgraph-checkpoint-postgres"
            ) from None
        saver = stack.enter_context(PostgresSaver.from_conn_string(uri))
        saver.setup()
        yield saver


def get_checkpointer(
    backend: str = "memory",
    conn_string: str | None = None,
) -> MemorySaver:
    """Retorna um checkpointer para uso direto (apenas memory)."""
    resolved_backend, _ = resolve_checkpoint_target(backend, conn_string)
    if resolved_backend == "memory":
        return get_checkpointer_memory()
    raise ValueError(
        "Para sqlite/postgres use get_checkpointer_cm(backend, conn_string) e execute o app dentro do context manager."
    )
