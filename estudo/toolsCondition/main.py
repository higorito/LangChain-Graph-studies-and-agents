from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tracers.stdout import FunctionCallbackHandler
from langgraph.graph.state import RunnableConfig
from rich.pretty import pprint
from rich.markdown import Markdown
from typing import Literal

from toolsCondition.graph import build_graph

def main() -> None:
    graph = build_graph()
    
    fn_hd_callback = FunctionCallbackHandler(function=print)
    
    user_type: Literal["plus", "free"] = "plus"
    config = RunnableConfig(
        run_name="test_name",
        tags=["test_tag"],
        configurable={'thread_id': 999, 'user_type': user_type},
        max_concurrency=2,
        recursion_limit=25,
        # callbacks=[fn_hd_callback]
    ) #varias configs, pde ser no context tbm. aqui pode ser trocado em cada node

    input = "faça 44 vezes 33"
    human_message = HumanMessage(content=input)

    current_messages = [human_message]
    response = graph.invoke({"messages": current_messages}, config=config)
    
    last_message = response["messages"][-1]
    
    # if isinstance(last_message, AIMessage):
    #     model_name = last_message.response_metadata.get("model", "")
    #     print(f"{model_name=}")

    pprint(response)
    print(Markdown( "---"))
    pprint(response["messages"][-1].content)

if __name__ == "__main__":
    main()