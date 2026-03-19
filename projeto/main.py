"""
Entry point do Agente de Atribuicao de Movimento.

Uso:
    python -m projeto.main run                    # analise com ticker padrao (PETR4.SA)
    python -m projeto.main run PETR4.SA          # analise de um ativo
    python -m projeto.main run PETR4.SA --date 2025-02-18 --provider openrouter --model openai/gpt-4o-mini
    python -m projeto.main chat                   # modo conversacional (Gemini por padrao)
    python -m projeto.main chat --provider ollama --model gpt-oss:20b-cloud
"""
import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(dotenv_path=find_dotenv(), override=True)


def run_agent(
    ticker: str = "PETR4.SA",
    date: str = "today",
    model: str | None = None,
    provider: str | None = None,
    silent: bool = False,
) -> dict:
    from projeto.agent_base.runtime import (
        build_runnable_config,
        collect_graph_updates,
        stream_graph_updates,
    )
    from projeto.agents.atribuicao_movimento import build_graph
    from projeto.config import LLM_MODEL, LLM_PROVIDER
    from projeto.display import print_agent_start, print_error, print_node_progress
    from projeto.state import InputState

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
        agent_input = {"ticker": user_input.ticker, "date": user_input.date}
        run_config = build_runnable_config(model=model, provider=provider)

        if silent:
            return collect_graph_updates(graph, agent_input, config=run_config)

        final_state: dict = {}
        for node_name, node_output in stream_graph_updates(graph, agent_input, config=run_config):
            print_node_progress(node_name)
            if isinstance(node_output, dict):
                final_state.update(node_output)

        return final_state
    except Exception as error:
        if not silent:
            print_error("Falha fatal na execucao do agente.", error=error)
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
        help="Provedor LLM: ollama, google_genai (ou google/gemini), openrouter",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agente Financeiro de Atribuicao de Movimento",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s run                          # analise PETR4.SA, data hoje, modelo padrao
  %(prog)s run NVDA --provider openrouter --model openai/gpt-4o-mini
  %(prog)s run PETR4.SA --date 2025-02-18
  %(prog)s chat                         # modo conversacional (Gemini por padrao)
  %(prog)s chat --provider ollama --model gpt-oss:20b-cloud
        """.strip(),
    )
    subparsers = parser.add_subparsers(dest="cmd", help="Comando: run (analise one-shot) ou chat")

    run_p = subparsers.add_parser("run", help="Executa analise de atribuicao de movimento para um ativo")
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
        help="Data do pregao: YYYY-MM-DD ou today (default: today)",
    )
    _parse_llm_options(run_p)

    chat_p = subparsers.add_parser("chat", help="Modo conversacional com memoria e Gemini como padrao")
    _parse_llm_options(chat_p)
    chat_p.add_argument(
        "--checkpoint",
        type=str,
        default="memory",
        choices=("memory", "sqlite", "postgres"),
        help="Backend de persistencia da conversa: memory, sqlite ou postgres",
    )
    chat_p.add_argument(
        "--checkpoint-uri",
        type=str,
        default=None,
        help="SQLite: caminho do arquivo. Postgres: DSN (ou use CHECKPOINT_POSTGRES_URI)",
    )
    chat_p.add_argument(
        "--thread-id",
        type=str,
        default="sessao_terminal_1",
        help="ID da thread/sessao",
    )

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
        from projeto.display import display_result

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
            checkpoint_backend=getattr(args, "checkpoint", "memory"),
            checkpoint_conn_string=getattr(args, "checkpoint_uri", None),
            thread_id=getattr(args, "thread_id", "sessao_terminal_1"),
        )
        return

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
