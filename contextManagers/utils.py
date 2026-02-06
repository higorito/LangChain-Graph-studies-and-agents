from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, cast
from langchain.chat_models import init_chat_model, BaseChatModel

def load_llm() -> BaseChatModel:
    model = cast("BaseChatModel", init_chat_model(model="gpt-oss:20b-cloud", model_provider="ollama", configurable_fields="any"))
    
    assert hasattr(model, "bind_tools")
    assert hasattr(model, "with_config")
    assert hasattr(model, "invoke")
    return model

class Connection:
    def open_connection(self) -> None:
        print("Connection opened.")

    def close_connection(self) -> None:
        print("Connection closed.")

    def execute_query(self) -> None:
        print("--------------Executing query--------------")

@lru_cache
def get_connection() -> Connection:
    return Connection() 

@contextmanager
def sync_lifespan() -> Generator[None]:
    print("Starting up resources...")
    yield get_connection() #acima quando inicia, abaixo quando termina
    print("Finishing up resources... SYNC")