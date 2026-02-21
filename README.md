# LangChain Graph Studies & Agents: Atribuição de Movimento

Agente heurístico e quantitativo para explicação de movimentos diários de ações da B3 usando LangGraph e Yahoo Finance.

## Como Executar

O pipeline pode ser executado de algumas maneiras na CLI principal:

### 1. Modo Interativo (Chat)
Inicia uma sessão conversacional com memória. O agente deduz qual ativo e data analisar com base nas suas perguntas.
```bash
python -m projeto.main chat                   # modo conversacional
python -m projeto.main chat --provider ollama --model gpt-oss:20b-cloud
```

### 2. Modo One-Shot (Direto)
Executa o grafo sem interatividade, extraindo os dados e retornando o JSON estruturado diretamente no terminal.
```bash
python -m projeto.main run                    # análise com ticker padrão (PETR4.SA)
python -m projeto.main run PETR4.SA          # análise de um ativo
python -m projeto.main run PETR4.SA --date 2025-02-18 --provider openrouter --model openai/gpt-4o-mini
```

> **Para mais detalhes sobre as bibliotecas, chamadas e o design do chatbot, veja a pasta `projeto/docs/`.**