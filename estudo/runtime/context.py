from dataclasses import dataclass
from typing import Literal

#contexto usado p dados imutaveis, userid, usertype conexao com bd, api key, etc... nao precisa serializar pq ta em runtime e nao vai pra llm
@dataclass(frozen=True, kw_only=True, slots=True)
class Context:
    user_type: Literal["plus", "free"] = "plus"
