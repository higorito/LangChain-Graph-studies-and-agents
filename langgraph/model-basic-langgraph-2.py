from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, add_messages, START, END
from dataclasses import dataclass


@dataclass
class State:
    nodes_path: Annotated[list[str], add_messages]
    number: int = 0
    
def node1(state: State) -> State:
    output: State = State(nodes_path=["node1"], number=state.number)
    
    print("Node 1 output", f"{state=}", f"{output=}")
    return output

def node2(state: State) -> State:
    output: State = State(nodes_path=["node2"], number=state.number)
    
    print("Node 2 output", f"{state=}", f"{output=}")
    return output


def node3(state: State) -> State:
    output: State = State(nodes_path=["node3"], number=state.number)
    
    print("Node 3 output", f"{state=}", f"{output=}")
    return output


def condition(state: State) -> Literal["node2", "node3"]:
    if state.number >= 10:
        return "node3"
    return "node2"


builder = StateGraph(State)

builder.add_node("node1", node1)
builder.add_node("node2", node2)
builder.add_node("node3", node3)

builder.add_edge(START, "node1")
builder.add_conditional_edges("node1", condition, ["node2", "node3"])
builder.add_edge("node2", END)
builder.add_edge("node3", END)

graph = builder.compile()

graph.get_graph().draw_mermaid_png(output_file_path="graph2.png")

response = graph.invoke({"nodes_path": []})

print("\n")
print(f"{response=}\n")


response = graph.invoke({"nodes_path": [], "number": 15})

print("\n")
print(f"{response=}")