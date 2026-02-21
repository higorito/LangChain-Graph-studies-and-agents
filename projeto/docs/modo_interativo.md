# Modo Interativo Conversacional (V1.2)

O Agente de Atribuição de Movimento agora possui um **Modo Interativo** que permite conversas em texto natural (chat) com o usuário no terminal. Ele atua como uma interface inteligente sobre a pipeline original (V1).

## Arquitetura

1. **ReAct Agent (`create_react_agent`)**: O fluxo não determinístico é gerenciado pelo LangGraph usando o paradigma ReAct (Reasoning and Acting).
2. **MemorySaver (Checkpointer)**: Integrado diretamente ao agente conversacional, mantendo o histórico da conversa entre turnos. O usuário pode fazer perguntas de acompanhamento sobre a mesma ação (ex: "e quais as notícias?") sem precisar repetir o ticker.
3. **Tool `analisar_acao`**: O fluxo V1 (orquestrado pela função `run_agent`) foi abstraído e injetado no ReAct Agent como uma Ferramenta (Tool). Dessa forma, a LLM conversacional decide autônomamente quando é necessário ler dados fundamentalistas/heurísticos antes de responder ao usuário.

## Como Executar

### 1. Iniciar o Chat (Modo Interativo)
Se você omitir o parâmetro de ação (ticker), a CLI automaticamente iniciará o modo interativo.

```bash
python -m projeto.main
```

Exemplo de Interação:
```text
🗣️  Modo Interativo Iniciado (Digite 'sair', 'quit' ou 'exit' para fechar)
Eu sou seu assistente financeiro. Sobre qual ativo vamos conversar hoje?

Você: Olá, como foram os resultados de PETR4 hoje?
... Pensando & Acionando Ferramentas: analisar_acao ...
Assistente: A Petrobras apresentou uma alta de...
```

### 2. Modo Isolado (Legacy / One-shot)
Caso queira disparar a pipeline imediatamente sem interagir em um chat, basta providenciar o Ticker como argumento posicional. O agente irá contornar a camada conversacional e executar a análise linear.

```bash
# Executa apenas o grafo linear determinístico e retorna o JSON estruturado
python -m projeto.main VALE3.SA
```

## Configurações e Logs
- Como o `run_agent` foi envolvido em uma tool padrão do LangChain, foram aplicados ajustes técnicos de encoding (remoção do `ensure_ascii=False`) e serialização (cast de `numpy.float64` para `float` nativo) garantindo funcionamento estável no terminal Windows (`cp1252`) e na serialização do `MemorySaver` (msgpack).
- O agente aceita repasses dinâmicos para seleção de LLMs usando as flags originais (`--model` e `--provider`).

```bash
python -m projeto.main --model gemini-2.5-flash --provider google_genai
```
