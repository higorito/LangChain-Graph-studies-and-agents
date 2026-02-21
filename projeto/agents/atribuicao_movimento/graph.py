from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from projeto.state import AgentState, InputState, OutputState
from projeto.agents.atribuicao_movimento import nodes

_FETCH_NODES = ["fetch_stock_data", "fetch_index_data", "fetch_sector_data", "fetch_news"]
_JUNCTION_NODE = "compute_metrics"


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(
        AgentState,
        input=InputState,
        output=OutputState,
    )
    retry = RetryPolicy(max_attempts=3)
    builder.add_node("fetch_stock_data", nodes.fetch_stock_data, retry=retry)
    builder.add_node("fetch_index_data", nodes.fetch_index_data, retry=retry)
    builder.add_node("fetch_sector_data", nodes.fetch_sector_data, retry=retry)
    builder.add_node("fetch_news", nodes.fetch_news, retry=retry)
    builder.add_node("compute_metrics", nodes.compute_metrics)
    builder.add_node("classify_movement", nodes.classify_movement)
    builder.add_node("generate_explanation", nodes.generate_explanation)

    for node_name in _FETCH_NODES:
        builder.add_edge(START, node_name)
    for node_name in _FETCH_NODES:
        builder.add_edge(node_name, _JUNCTION_NODE)
    builder.add_edge("compute_metrics", "classify_movement")
    builder.add_edge("classify_movement", "generate_explanation")
    builder.add_edge("generate_explanation", END)

    return builder.compile()
