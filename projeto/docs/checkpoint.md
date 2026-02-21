# Checkpointer (persistência do chat)

O modo chat usa um **checkpointer** para guardar o estado da conversa (memória entre turnos). O módulo genérico está em `projeto.agent_base.checkpoint`.

## Backends

| Backend   | Uso                    | Persistência        |
|-----------|------------------------|---------------------|
| **memory** | Padrão, sem dependência | Só na sessão (perde ao sair) |
| **sqlite** | Arquivo local          | Persiste no arquivo |
| **postgres** | Produção / multi-processo | Persiste no Postgres |

## Uso na CLI

```bash
# Memória em RAM (padrão)
python -m projeto.main chat

# SQLite (arquivo) — requer: pip install langgraph-checkpoint-sqlite
python -m projeto.main chat --checkpoint sqlite --checkpoint-uri ./data/chat.db

# SQLite em memória (útil para testes)
python -m projeto.main chat --checkpoint sqlite --checkpoint-uri ":memory:"

# Postgres — requer: pip install langgraph-checkpoint-postgres e Postgres rodando
# no windows requer pip install psycopg-binary
python -m projeto.main chat --checkpoint postgres --checkpoint-uri "postgresql://postgres:postgres@localhost:5432/langgraph"
# ou defina CHECKPOINT_POSTGRES_URI no ambiente
python -m projeto.main chat --checkpoint postgres

# Thread ID (várias conversas com sqlite/postgres)
python -m projeto.main chat --checkpoint sqlite --checkpoint-uri ./chat.db --thread-id usuario_1
```

## Docker (Postgres)

Suba o Postgres com o Compose do projeto:

```bash
cd projeto
docker compose up -d postgres
```

DSN de conexão: `postgresql://postgres:postgres@localhost:5432/langgraph`

Em seguida:

```bash
pip install langgraph-checkpoint-postgres
python -m projeto.main chat --checkpoint postgres --checkpoint-uri "postgresql://postgres:postgres@localhost:5432/langgraph"
```

## API (módulo genérico)

- `get_checkpointer("memory")` — retorna `MemorySaver()` para uso direto.
- `get_checkpointer_cm(backend, conn_string)` — context manager para qualquer backend; use para sqlite/postgres e rode o app dentro do `with`.
- `get_checkpointer_sqlite(conn_string)` / `get_checkpointer_postgres(conn_string)` — context managers específicos.

O grafo é compilado com `builder.compile(checkpointer=...)`. O `config["configurable"]["thread_id"]` identifica a sessão.
