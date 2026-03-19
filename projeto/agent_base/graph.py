from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy


StateNode = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class GraphNodeSpec:
    name: str
    handler: StateNode
    retry: RetryPolicy | None = None


def create_state_graph(
    state_schema: type[Any],
    *,
    input_schema: type[Any] | None = None,
    output_schema: type[Any] | None = None,
) -> StateGraph:
    return StateGraph(state_schema, input=input_schema, output=output_schema)


def add_graph_nodes(builder: StateGraph, nodes: Sequence[GraphNodeSpec]) -> None:
    for node in nodes:
        kwargs = {"retry": node.retry} if node.retry is not None else {}
        builder.add_node(node.name, node.handler, **kwargs)


def add_sequence_nodes(builder: StateGraph, nodes: Sequence[GraphNodeSpec]) -> None:
    if not nodes:
        raise ValueError("nodes must not be empty")

    if any(node.retry is not None for node in nodes):
        add_graph_nodes(builder, nodes)
        for current, following in zip(nodes, nodes[1:]):
            builder.add_edge(current.name, following.name)
        return

    builder.add_sequence([(node.name, node.handler) for node in nodes])


def build_parallel_then_sequence_graph(
    state_schema: type[Any],
    *,
    input_schema: type[Any] | None = None,
    output_schema: type[Any] | None = None,
    parallel_nodes: Sequence[GraphNodeSpec],
    sequence_nodes: Sequence[GraphNodeSpec],
    compile_kwargs: dict[str, Any] | None = None,
) -> CompiledStateGraph:
    if not parallel_nodes:
        raise ValueError("parallel_nodes must not be empty")
    if not sequence_nodes:
        raise ValueError("sequence_nodes must not be empty")

    builder = create_state_graph(
        state_schema,
        input_schema=input_schema,
        output_schema=output_schema,
    )
    add_graph_nodes(builder, parallel_nodes)
    add_sequence_nodes(builder, sequence_nodes)

    first_sequence_node = sequence_nodes[0].name
    last_sequence_node = sequence_nodes[-1].name

    for node in parallel_nodes:
        builder.add_edge(START, node.name)
        builder.add_edge(node.name, first_sequence_node)
    builder.add_edge(last_sequence_node, END)

    return builder.compile(**(compile_kwargs or {}))
