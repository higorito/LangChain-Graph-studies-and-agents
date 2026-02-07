from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, kw_only=True, slots=True)
class Context:
    user_type: Literal["plus", "free"] = "plus"
