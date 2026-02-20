import os
from typing import Literal, overload

@overload
def get_env(name: str) -> str: ...
@overload
def get_env(name: str, strict: bool = Literal[True]) -> str: ...
@overload
def get_env(name: str, strict: bool = Literal[False]) -> str | None: ...

def get_env(name: str, strict: bool = True) -> str | None:
    value = os.getenv(name)

    if value is None and strict:
        raise ValueError(f"Environment variable '{name}' not found.")

    return value