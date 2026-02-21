"""
Entry point do Agente de Atribuição de Movimento.

Uso:
    python -m projeto.main run                    # análise com ticker padrão (PETR4.SA)
    python -m projeto.main run PETR4.SA          # análise de um ativo
    python -m projeto.main run PETR4.SA --date 2025-02-18 --provider openrouter --model openai/gpt-4o-mini
    python -m projeto.main chat                   # modo conversacional
    python -m projeto.main chat --provider ollama --model gpt-oss:20b-cloud
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
    silent: bool = False,
) -> dict:
    user_input = InputState(ticker=ticker, date=date)
    active_model = model or LLM_MODEL
    active_provider = provider or LLM_PROVIDER

    if not silent:
        print_agent_start(
            ticker=user_input.ticker,
            date=user_input.date,
            model=active_model,
            provider=active_provider,
        )

    try:
        graph = build_graph()
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
                if not silent:
                    print_node_progress(node_name)
                final_state.update(node_output)

        return final_state

    except Exception as e:
        if not silent:
            print_error("Falha fatal na execução do agente.", error=e)
            sys.exit(1)
        raise


def _parse_llm_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modelo LLM (ex: gemini-2.0-flash, gpt-oss:20b-cloud, openai/gpt-4o-mini)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Provedor LLM: ollama, google_genai (ou google), openrouter",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agente Financeiro de Atribuição de Movimento",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s run                          # análise PETR4.SA, data hoje, modelo padrão
  %(prog)s run NVDA --provider openrouter --model openai/gpt-4o-mini
  %(prog)s run PETR4.SA --date 2025-02-18
  %(prog)s chat                         # modo conversacional
  %(prog)s chat --provider ollama --model gpt-oss:20b-cloud
        """.strip(),
    )
    subparsers = parser.add_subparsers(dest="cmd", help="Comando: run (análise one-shot) ou chat (conversacional)")

    run_p = subparsers.add_parser("run", help="Executa análise de atribuição de movimento para um ativo")
    run_p.add_argument(
        "ticker",
        nargs="?",
        default="PETR4.SA",
        help="Ticker ou nome do ativo (default: PETR4.SA)",
    )
    run_p.add_argument(
        "--date",
        type=str,
        default="today",
        help="Data do pregão: YYYY-MM-DD ou today (default: today)",
    )
    _parse_llm_options(run_p)

    chat_p = subparsers.add_parser("chat", help="Modo conversacional com memória (ferramentas: análise, comparação, etc.)")
    _parse_llm_options(chat_p)

    argv = sys.argv[1:]
    if "run" not in argv and "chat" not in argv:
        if not argv:
            argv = ["chat"]
        elif argv[0].startswith("-"):
            argv = ["chat"] + argv
        else:
            argv = ["run", argv[0]] + argv[1:]
    args = parser.parse_args(argv)

    if args.cmd == "run":
        result = run_agent(
            ticker=args.ticker,
            date=args.date,
            model=args.model,
            provider=args.provider,
        )
        if result:
            display_result(result)
        return

    if args.cmd == "chat" or args.cmd is None:
        from projeto.interactive import run_interactive_mode
        run_interactive_mode(
            model=getattr(args, "model", None),
            provider=getattr(args, "provider", None),
        )
        return

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
