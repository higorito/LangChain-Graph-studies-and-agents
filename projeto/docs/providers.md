# Guia do Sistema Modular de Provedores LLM

## Visão Geral

O sistema foi refatorado para ser modular e suportar múltiplos provedores de LLM de forma fácil e extensível.


**Uso**:
```bash
export OPENROUTER_API_KEY="sua-chave-aqui"
python -m projeto.main NVDA --model openai/gpt-4o-mini --provider openrouter
python -m projeto.main TSLA --model anthropic/claude-3.5-sonnet --provider openrouter
```

## Como Funciona o Sistema Modular

### Arquitetura

```
providers.py (BaseLLMProvider, subclasses por provedor)
    ↓
config.py (usa DEFAULT_MODELS)
    ↓
utils.py (load_llm, load_structured_llm)
    ↓
nodes.py (usa o LLM configurado)
```

### Classes Principais

**BaseLLMProvider**: Classe abstrata que define interface comum
- `get_supported_models()`: Lista modelos suportados
- `get_model_config(model)`: Retorna configuração específica
- `validate_api_key()`: Valida se API key está configurada

**Provedores Concretos**:
- `OllamaProvider`: Para modelos locais
- `GeminiProvider`: Para Gemini cloud
- `OpenRouterProvider`: Para agregador multi-modelo

## Adicionando um Novo Provedor

```bash
python -m projeto.main PETR4.SA --model gpt-oss:20b-cloud --provider ollama

python -m projeto.main PETR4.SA --model gemini-2.5-flash --provider google

python -m projeto.main PETR4.SA --model openai/gpt-4o-mini --provider openrouter
```