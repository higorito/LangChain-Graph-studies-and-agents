"""
Entry point do Agente de Atribuição de Movimento V1.

- Streaming com graph.stream() — mostra progresso de cada nó
- Input validado via InputState (Pydantic)
- UI Desacoplada: formatação visual totalmente separada no módulo `display`
- Resiliência: try/except abrangente para erros do grafo

Uso:
    python -m projeto.main
    python -m projeto.main PETR4.SA 2025-02-18
"""
import argparse
import sys

from dotenv import load_dotenv, find_dotenv
load_dotenv(dotenv_path=find_dotenv(), override=True)

from projeto.agents.atribuicao_movimento import build_graph
from projeto.state import InputState
from projeto.config import LLM_MODEL, LLM_PROVIDER
from projeto.display import print_agent_start, print_node_progress, display_result, print_error

def run_agent(
    ticker: str = "PETR4.SA",
    date: str = "today",
    model: str | None = None,
    provider: str | None = None,
) -> dict:
    """Executa o agente com streaming — mostra progresso de cada nó.

    Args:
        ticker: Símbolo do ativo
        date: Data do pregão ("YYYY-MM-DD" ou "today")
        model: Opcional. Sobrescreve o modelo LLM do config.py
        provider: Opcional. Sobrescreve o provedor LLM do config.py

    Returns:
        Estado final do grafo com todos os dados e a explicação
    """
    user_input = InputState(ticker=ticker, date=date)
    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER

    print_agent_start(
        ticker=user_input.ticker,
        date=user_input.date,
        model=active_model,
        provider=active_provider
    )

    try:
        graph = build_graph()

        # Essa configuração será repassada automaticamente até o nó que tem LLM,
        # sobrescrevendo os valores da init_chat_model !
        configurable = {}
        if model:
            configurable["model"] = model
        if provider:
            configurable["model_provider"] = provider

        final_state = {}
        for event in graph.stream(
            {"ticker": user_input.ticker, "date": user_input.date},
            config={"configurable": configurable} if configurable else None,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                print_node_progress(node_name)
                final_state.update(node_output)

        return final_state
    
    except Exception as e:
        print_error("Falha fatal na execução do agente.", error=e)
        sys.exit(1)


def main() -> None:
    """Entry point CLI turbinado com lógica interativa e one-shot."""
    
    parser = argparse.ArgumentParser(description="Agente Financeiro de Atribuição de Movimento")
    
    # Se omitido, lança o modo chat.
    parser.add_argument("ticker", nargs="?", default=None, help="Símbolo do ativo (ex: PETR4.SA). Se omitido, inicia o modo chat interativo.")
    parser.add_argument("date", nargs="?", default="today", help="Data: YYYY-MM-DD ou today")
    
    # Argumentos para o módulo LLM
    parser.add_argument("--model", type=str, help="Ex: gemini-2.5-flash, llama3.1")
    parser.add_argument("--provider", type=str, help="Ex: google_genai, ollama, openai")

    args = parser.parse_args()

    # Modo Interativo (Chat)
    if not args.ticker:
        from projeto.interactive import run_interactive_mode
        run_interactive_mode(model=args.model, provider=args.provider)
        
    # Modo One-shot (Execução isolada)
    else:
        result = run_agent(
            ticker=args.ticker,
            date=args.date,
            model=args.model,
            provider=args.provider
        )
        
        if result:
            display_result(result)


if __name__ == "__main__":
    main()
