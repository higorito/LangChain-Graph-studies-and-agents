from contextlib import asynccontextmanager
from typing import AsyncGenerator, cast
from langchain.chat_models import init_chat_model, BaseChatModel

def load_llm() -> BaseChatModel:
    model = cast("BaseChatModel", init_chat_model(model="gpt-oss:20b-cloud", model_provider="ollama", configurable_fields="any"))
    
    assert hasattr(model, "bind_tools")
    assert hasattr(model, "with_config")
    assert hasattr(model, "invoke")
    return model

@asynccontextmanager
async def async_lifespan() -> AsyncGenerator[None]:
    print("Starting up resources...")
    yield
    print("Finishing up resources... ASYNC")