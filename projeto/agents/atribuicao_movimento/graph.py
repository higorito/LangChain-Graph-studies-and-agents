from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from projeto.agent_base import GraphNodeSpec, build_parallel_then_sequence_graph
from projeto.agents.atribuicao_movimento import nodes
from projeto.state import AgentState, InputState, OutputState

_RETRY = RetryPolicy(max_attempts=3)
_FETCH_NODES = (
    GraphNodeSpec("fetch_stock_data", nodes.fetch_stock_data, retry=_RETRY),
    GraphNodeSpec("fetch_index_data", nodes.fetch_index_data, retry=_RETRY),
    GraphNodeSpec("fetch_sector_data", nodes.fetch_sector_data, retry=_RETRY),
    GraphNodeSpec("fetch_news", nodes.fetch_news, retry=_RETRY),
)
_PIPELINE_NODES = (
    GraphNodeSpec("compute_metrics", nodes.compute_metrics),
    GraphNodeSpec("classify_movement", nodes.classify_movement),
    GraphNodeSpec("generate_explanation", nodes.generate_explanation),
)


def build_graph() -> CompiledStateGraph:
    return build_parallel_then_sequence_graph(
        AgentState,
        input_schema=InputState,
        output_schema=OutputState,
        parallel_nodes=_FETCH_NODES,
        sequence_nodes=_PIPELINE_NODES,
    )
