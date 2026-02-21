# Estrutura modular do projeto

## Camadas

- **agent_base**: Base reutilizável (state, providers, llm). Sem regra de negócio.
- **agents**: Agentes concretos. Cada um tem graph, nodes e prompts.
- **projeto (raiz)**: Config, state específico, tools compartilhados, main e interactive.

## agent_base

- `state.py`: BaseInputState, BaseAgentState, BaseOutputState (Pydantic). Estender para definir entrada/saída do agente.
- `providers.py`: Provedores LLM (Ollama, Gemini, OpenRouter). `get_chat_model_kwargs(provider, model)` → kwargs para `init_chat_model`.
- `llm.py`: `load_llm`, `load_structured_llm` usando os provedores.

## agents/atribuicao_movimento

Agente de atribuição de movimento (por que o ativo subiu/caiu).

- `graph.py`: `build_graph()` — StateGraph com fan-out/fan-in (fetch paralelo) e pipeline compute → classify → explain.
- `nodes.py`: Nós do grafo (fetch, compute_metrics, classify_movement, generate_explanation).
- `prompts.py`: System e human prompts do LLM.

Estado (InputState, AgentState, OutputState) e config (THRESHOLDS, TICKER_SECTOR_MAP) ficam na raiz do projeto porque são compartilhados com main/display/tools.

## Como derivar outro agente

1. Criar `agents/novo_agente/` com `__init__.py`, `graph.py`, `nodes.py`, `prompts.py` (se usar LLM).
2. Definir state em `state.py` (ou em um módulo do agente) herdando de `BaseInputState` / `BaseAgentState` / `BaseOutputState` se fizer sentido.
3. Usar `load_llm` / `load_structured_llm` de `agent_base` nos nós que precisam de LLM.
4. Em `main` ou outro entrypoint, importar `build_graph` do novo agente e invocar o grafo.

Tools podem ficar em `projeto/tools/` (compartilhados) ou dentro do agente se forem específicos.
