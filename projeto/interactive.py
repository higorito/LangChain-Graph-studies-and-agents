"""
Módulo interativo conversacional (V1.2) para o Agente de Atribuição de Movimento.

Utiliza 'create_react_agent' do LangGraph com 'MemorySaver' para manter
o contexto da conversa. Expõe a execução do pipeline analítico (V1) como uma Tool.
"""
from typing import TypedDict
import json

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from projeto.config import LLM_MODEL, LLM_PROVIDER, resolve_ticker
from projeto.display import console
from projeto.main import run_agent
from projeto.utils import load_llm

_llm_instance = None
_active_model = None
_active_provider = None


def _get_llm():
    global _llm_instance
    return _llm_instance


def _set_llm(llm):
    global _llm_instance
    _llm_instance = llm


def _get_model_provider():
    global _active_model, _active_provider
    return _active_model, _active_provider


def _set_model_provider(model, provider):
    global _active_model, _active_provider
    _active_model = model
    _active_provider = provider


@tool
def analisar_acao(ticker: str, data: str = "today") -> str:
    """Ferramenta para executar a análise fundamentalista e quantitativa completa de uma ação/ticker.
    
    Use SEMPRE que o usuário mencionar:
    - Nomes de empresas (ex: "Nvidia", "Petrobras", "Apple")
    - Tickers (ex: "NVDA", "PETR4.SA", "AAPL")
    - Perguntas sobre variação de preço, queda, alta, notícias
    
    A ferramenta já converte nomes de empresas em tickers automaticamente.

    Args:
        ticker: Símbolo da ação OU nome da empresa (ex: "NVDA", "Nvidia", "PETR4.SA", "Petrobras").
        data: Data da análise no formato "YYYY-MM-DD" ou "today" para o pregão atual. Padrão: "today".

    Returns:
        JSON em formato string com o resultado da análise (métricas, classificação e explicação detalhada).
    """
    # Resolve nome da empresa para ticker (tenta mapeamento estático primeiro)
    resolved_ticker = resolve_ticker(ticker)
    
    # Se não encontrou no mapeamento, usa LLM como fallback
    llm = _get_llm()
    if llm and resolved_ticker == ticker.upper():
        try:
            from pydantic import BaseModel
            
            class TickerSuggestion(BaseModel):
                ticker: str
                exchange: str
                confidence: str
            
            prompt = f"""Given the company name "{ticker}", suggest the correct stock ticker symbol.
If the company is Brazilian, add ".SA" suffix (e.g., VALE3.SA, PETR4.SA).
If American, use the standard ticker (e.g., AAPL, MSFT).
Respond with the ticker symbol only, nothing else."""
            
            structured_llm = llm.with_structured_output(TickerSuggestion)
            result = structured_llm.invoke(prompt)
            resolved_ticker = result.ticker
        except Exception:
            pass  # Se falhar, mantém o ticker original
    
    try:
        model, provider = _get_model_provider()
        resultado = run_agent(ticker=resolved_ticker, date=data, model=model, provider=provider)
        return json.dumps(resultado, indent=2)
    except Exception as e:
        return f"Erro ao executar a pipeline de análise para {resolved_ticker}: {str(e)}"


def run_interactive_mode(model: str | None = None, provider: str | None = None):
    """Inicializa o agente conversacional em loop infinito."""
    
    # so pra não poluir o terminal com warnings
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
    import logging
    logging.getLogger("langchain_core").setLevel(logging.ERROR)
    logging.getLogger("langchain_google_genai").setLevel(logging.ERROR)
    
    console.print("\n[bold green]🗣️  Modo Interativo Iniciado (Digite 'sair', 'quit' ou 'exit' para fechar)[/]")
    console.print("[dim]Eu sou seu assistente financeiro. Sobre qual ativo vamos conversar hoje?[/]\n")
    
    # Preparar LLM dinâmico
    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER
    
    console.print(f"[dim]Usando modelo: {active_model} | Provider: {active_provider}[/]\n")
    
    llm = load_llm(model=active_model, provider=active_provider)
    _set_llm(llm)
    _set_model_provider(active_model, active_provider)
    
    #TODO: implementar forma de passar configurações de model/provider dinamicamente pelo invoke
    # FICARA AQUI

    # Criar Agente ReAct com Ferramentas e Memória
    tools = [analisar_acao]
    memory = MemorySaver()
    
    
    system_prompt = """Você é um analista financeiro sênior especializado no mercado de ações (Bovespa B3 e exterior).
Você está conversando com um usuário no terminal. Seja direto, cordial e altamente profissional.

## Quando usar a ferramenta 'analisar_acao'

Use SEMPRE que o usuário mencionar qualquer uma destas situações:
1. Perguntar sobre variações de preço (subiu, caiu, alta, baixa)
2. Mencionar o nome de uma empresa ou ticker (ex: "Nvidia", "PETR4", "Apple", "ações da Petrobras")
3. Perguntar o motivo de algo relacionado a uma ação
4. Pedir notícias, análise ou informações sobre um ativo específico
5. Qualquer pergunta que exija dados concretos de mercado

A ferramenta aceita tanto tickers ("NVDA", "PETR4.SA") quanto nomes de empresas ("Nvidia", "Petrobras").

## Como responder

1. Quando o usuário mencionar uma empresa/ação, use a ferramenta 'analisar_acao' automaticamente
2. Analise o resultado JSONReturned pela ferramenta
3. Formate os dados de forma clara e conversational
4. Cite números específicos (percentuais, preços, volumes) quando disponíveis
5. Se a ferramenta retornar erro, informe o usuário educadamente

## Importante

- NÃO peça confirmação para usar a ferramenta — use-a diretamente quando identificar o ticker
- Se não conseguir identificar o ticker, faça uma pergunta direta para esclarecer
- NÃO tente inventar dados — sempre use a ferramenta quando precisar de informações de mercado"""

    app = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        prompt=system_prompt
    )

    # isolar diferentes conversas
    config = {"configurable": {"thread_id": "sessao_terminal_1"}}

    while True:
        try:
            user_input = input("Você: ")
            if user_input.lower() in ["sair", "quit", "exit", "q"]:
                console.print("\n[dim]Encerrando agente interativo... Até logo![/]")
                break
            if not user_input.strip():
                continue
                
            for event in app.stream({"messages": [("user", user_input)]}, config, stream_mode="values"):
                last_message = event["messages"][-1]
                
                if last_message.type == "ai" and last_message.content:
                    texto_resposta = ""
                    
                    # Gemini e outros LLMs podem retornar o content como lista de blocos (dict)
                    if isinstance(last_message.content, list):
                        for bloco in last_message.content:
                            if isinstance(bloco, dict) and "text" in bloco:
                                texto_resposta += bloco["text"]
                            elif isinstance(bloco, str):
                                texto_resposta += bloco
                    else:
                        texto_resposta = str(last_message.content)
                        
                    if texto_resposta.strip():
                        console.print(f"\n[bold blue]Assistente:[/] {texto_resposta.strip()}\n")

                # aviso tool calls
                elif last_message.type == "ai" and getattr(last_message, "tool_calls", None):
                    tool_names = [tc["name"] for tc in last_message.tool_calls]
                    console.print(f"\n[dim italic]... Pensando & Acionando Ferramentas: {', '.join(tool_names)} ...[/]")

        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrompido pelo usuário. Até logo![/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Erro inesperado:[/] {e}\n")
