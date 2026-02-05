from rich.pretty import pprint
from langchain_core.tools import tool, BaseTool
from langgraph.prebuilt import ToolRuntime

from runnableConfig.state import State
from runtime.context import Context

@tool
def multiply(x: float, y: float, runtime: ToolRuntime[Context, State]) -> float: #o legal que nao manda isso pra llm. ex: essa ferramenta vai la no banco de dados pegar info do user
    """Multiply x and y and return the result

    Args:
        x (float): The first number
        y (float): The second number

    Returns:
        float: The product of x and y
    """
    pprint(runtime)
    return x * y

@tool
def add(x: float, y: float) -> float:
    """Add x and y and return the result

    Args:
        x (float): The first number
        y (float): The second number

    Returns:
        float: The sum of x and y
    """
    return x + y

@tool
def subtract(x: float, y: float) -> float:
    """Subtract y from x and return the result

    Args:
        x (float): The first number
        y (float): The second number

    Returns:
        float: The difference of x and y
    """
    return x - y

@tool
def divide(x: float, y: float) -> float:
    """Divide x by y and return the result

    Args:
        x (float): The numerator
        y (float): The denominator

    Returns:
        float: The quotient of x and y
    """
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y


TOOLS: list[BaseTool] = [multiply, add, subtract, divide]
TOOLS_MAP = {t.name: t for t in TOOLS}

