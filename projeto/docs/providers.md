# Guia do Sistema Modular de Provedores LLM

## Visão Geral

Provedores ficam em `projeto.agent_base.providers`. Cada provedor implementa `get_chat_model_kwargs(model)` retornando kwargs para `init_chat_model` (LangChain). O carregamento do LLM está em `projeto.agent_base.llm`.

**Uso**:
```bash
export OPENROUTER_API_KEY="sua-chave-aqui"
python -m projeto.main NVDA --model openai/gpt-4o-mini --provider openrouter
python -m projeto.main TSLA --model anthropic/claude-3.5-sonnet --provider openrouter
python -m projeto.main PETR4.SA --model gemini-2.0-flash --provider google_genai
python -m projeto.main PETR4.SA --model gpt-oss:20b-cloud --provider ollama
```

## Arquitetura

```
agent_base/providers.py  (BaseLLMProvider, get_chat_model_kwargs)
    ↓
agent_base/llm.py       (load_llm, load_structured_llm)
    ↓
config.py               (LLM_MODEL, LLM_PROVIDER, DEFAULT_MODELS)
    ↓
agents/.../nodes.py     (usa load_structured_llm com config)
```

**Provedores**: `ollama`, `google_genai` (alias `google`), `openrouter`.

**BaseLLMProvider**:
- `get_supported_models()`: lista de modelos
- `get_chat_model_kwargs(model)`: dict para `init_chat_model(**kwargs)`
- `validate_api_key()`: bool

Para novo provedor: criar classe herdando `BaseLLMProvider`, implementar os três métodos e registrar em `_PROVIDERS`.
