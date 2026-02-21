# Modo interativo (chat)

O modo chat usa um **StateGraph** com **tools_condition** e **ToolNode** (LangGraph): o nó `call_llm` chama o LLM com ferramentas; pela condição `tools_condition` o fluxo vai para o nó `tools` ou para END; o nó `tools` executa as tool calls e volta para `call_llm`. Memória com **MemorySaver**.

## CLI

```bash
# Chat (padrão sem argumentos)
python -m projeto.main
python -m projeto.main chat
python -m projeto.main chat --provider ollama --model gpt-oss:20b-cloud

# Análise one-shot
python -m projeto.main run
python -m projeto.main run PETR4.SA
python -m projeto.main run NVDA --date today --provider openrouter --model openai/gpt-4o-mini
```

Sem subcomando: `python -m projeto.main` → chat; `python -m projeto.main PETR4.SA` → run PETR4.SA.

## Ferramentas do chat

| Ferramenta | Uso |
|------------|-----|
| **analisar_acao(ticker, data)** | Análise completa de atribuição de movimento. Aceita ticker ou nome (Petrobras, NVDA). |
| **resolver_ticker(nome_ou_ticker)** | Converte nome de empresa em ticker (ex: Petrobras → PETR4.SA). |
| **comparar_ativos(ticker1, ticker2, data)** | Compara dois ativos na mesma data (métricas e classificação). |

As tools chamam `run_agent(..., silent=True)` para não poluir o terminal com o progresso do pipeline.
