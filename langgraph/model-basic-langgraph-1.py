from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, add_messages

class State(TypedDict):
    nodes_path: Annotated[list[str], add_messages]
    
def node1(state: State) -> State:
    # output: State = {"nodes_path": [*nodes_path, "node1"]}
    output: State = {"nodes_path": ["node1"]}
    
    print("Node 1 output", f"{state=}", f"{output=}")
    return output

def node2(state: State) -> State:
    output: State = {"nodes_path": ["node2"]}
    
    print("Node 2 output", f"{state=}", f"{output=}")
    return output


builder = StateGraph(State)

builder.add_node("node1", node1)
builder.add_node("node2", node2)

builder.add_edge("__start__", "node1")
builder.add_edge("node1", "node2")
builder.add_edge("node2", "__end__")

graph = builder.compile()

# graph.get_graph().draw_mermaid_png(output_file_path="graph.png")

response = graph.invoke({"nodes_path": []})

print(f"{response=}")