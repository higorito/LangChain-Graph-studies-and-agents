from collections.abc import Sequence
from typing import TypedDict, Annotated
from langgraph.graph import add_messages
from langgraph.graph.message import BaseMessage

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]