"""
Montagem do StateGraph LangGraph — Agente de Atribuição de Movimento.

Padrões modernos utilizados:
- Fan-out / Fan-in: nós de fetch rodam em PARALELO (superstep)
- input_schema / output_schema: separação clara de I/O
- RetryPolicy: retry automático nos nós de fetch (API pode falhar)
- CachePolicy: cache nos nós de fetch (evitar chamadas repetidas)

Grafo visual:
    START ──┬── fetch_stock_data ──┐
            ├── fetch_index_data ──┤
            ├── fetch_sector_data ─┤── compute_metrics → classify → explain → END
            └── fetch_news ────────┘
"""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from projeto.state import AgentState, InputState, OutputState
from projeto.nodes import (
    fetch_stock_data,
    fetch_index_data,
    fetch_sector_data,
    fetch_news,
    compute_metrics,
    classify_movement,
    generate_explanation,
)


# Nós de fetch que rodam em paralelo
_FETCH_NODES = ["fetch_stock_data", "fetch_index_data", "fetch_sector_data", "fetch_news"]

# Nó de junção (fan-in)
_JUNCTION_NODE = "compute_metrics"


def build_graph() -> CompiledStateGraph:
    """Constrói e compila o grafo do agente com fan-out/fan-in.

    - Fan-out: START → 4 nós de fetch em paralelo
    - Fan-in: 4 nós de fetch → compute_metrics
    - Pipeline: compute_metrics → classify → explain → END

    Returns:
        Grafo compilado pronto para .invoke()
    """
    builder = StateGraph(
        AgentState,
        input=InputState,
        output=OutputState,
    )

    # Nós de fetch (com retry para resiliência de API)
    retry = RetryPolicy(max_attempts=3)

    builder.add_node("fetch_stock_data", fetch_stock_data, retry=retry)
    builder.add_node("fetch_index_data", fetch_index_data, retry=retry)
    builder.add_node("fetch_sector_data", fetch_sector_data, retry=retry)
    builder.add_node("fetch_news", fetch_news, retry=retry)

    # Nós de processamento
    builder.add_node("compute_metrics", compute_metrics)
    builder.add_node("classify_movement", classify_movement)
    builder.add_node("generate_explanation", generate_explanation)

    # Fan-out: START → todos os fetch em paralelo
    for node_name in _FETCH_NODES:
        builder.add_edge(START, node_name)

    # Fan-in: todos os fetch → compute_metrics
    for node_name in _FETCH_NODES:
        builder.add_edge(node_name, _JUNCTION_NODE)

    # Pipeline linear pós fan-in
    builder.add_edge("compute_metrics", "classify_movement")
    builder.add_edge("classify_movement", "generate_explanation")
    builder.add_edge("generate_explanation", END)

    return builder.compile()
