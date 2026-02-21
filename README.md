# LangChain Graph Studies & Agents: Atribuição de Movimento

Agente heurístico e quantitativo para explicação de movimentos diários de ações da B3 usando LangGraph e Yahoo Finance.

## Como Executar (V1.2)

O pipeline pode ser executado de duas maneiras na CLI principal:

### 1. Modo Interativo (Chat)
Inicia uma sessão conversacional com memória. O agente deduz qual ativo e data analisar com base nas suas perguntas.
```bash
python -m projeto.main
```

### 2. Modo One-Shot (Direto)
Executa o grafo sem interatividade, extraindo os dados e retornando o JSON estruturado diretamente no terminal.
```bash
python -m projeto.main PETR4.SA
```

> **Para mais detalhes sobre as bibliotecas, chamadas e o design do chatbot, veja a pasta `projeto/docs/`.**