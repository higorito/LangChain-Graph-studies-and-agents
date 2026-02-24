"""
Modulo de exibicao visual (UI) para o Agente de Atribuicao de Movimento.

Desacopla a formatacao do terminal (usando Rich) da logica principal do entrypoint.
"""
import json

from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint

console = Console()

_TYPE_EMOJI = {
    "macro": "[MACRO]",
    "setorial": "[SETORIAL]",
    "company_specific": "[EMPRESA]",
    "technical_flow": "[TECNICO]",
}

_NODE_LABELS = {
    "fetch_stock_data": "Buscando dados do ativo...",
    "fetch_index_data": "Buscando dados do indice...",
    "fetch_sector_data": "Buscando dados do setor...",
    "fetch_news": "Buscando noticias...",
    "compute_metrics": "Calculando metricas...",
    "classify_movement": "Classificando movimento...",
    "generate_explanation": "[LLM] Gerando explicacao [LLM]",
}


def print_agent_start(ticker: str, date: str, model: str, provider: str) -> None:
    """Exibe o cabecalho inicial da execucao do agente."""
    console.print(
        Panel(
            f"[bold cyan]Ticker:[/] {ticker}\n"
            f"[bold cyan]Data:[/] {date}\n"
            f"[bold cyan]Modelo:[/] {model}\n"
            f"[bold cyan]Provider:[/] {provider}",
            title=" Agente de Atribuicao de Movimento V1 ",
            border_style="cyan",
        )
    )
    console.print()


def print_node_progress(node_name: str) -> None:
    """Exibe o progresso de um no recem-concluido no stream do grafo."""
    label = _NODE_LABELS.get(node_name, f"{node_name}")
    console.print(f"  [dim]{label}[/] [green]OK[/]")


def display_result(result: dict) -> None:
    """Exibe o resultado final formatado no terminal."""
    console.print()

    metrics = result.get("metrics", {})
    classification = result.get("classification", {})
    explanation = result.get("explanation", "")
    parsed = _try_parse_json(explanation)
    explanation_text = parsed.get("explanation", explanation) if parsed else explanation

    console.print(
        Panel(
            f"[bold]Variacao do ativo:[/]  {metrics.get('price_change_pct', 0):.2f}%\n"
            f"[bold]Variacao do indice:[/] {metrics.get('index_change_pct', 0):.2f}%\n"
            f"[bold]Variacao do setor:[/]  {metrics.get('sector_change_pct', 0):.2f}%\n"
            f"[bold]Volume ratio:[/]       {metrics.get('volume_ratio', 0):.2f}x\n"
            f"[bold]Anomalia de volume:[/] {'SIM' if metrics.get('volume_anomaly') else 'Nao'}\n"
            f"[bold]Tendencia mercado:[/]  {metrics.get('market_trend', '?')}",
            title="Metricas",
            border_style="green",
        )
    )

    mv_type = classification.get("movement_type", "?")
    emoji = _TYPE_EMOJI.get(mv_type, "?")

    console.print(
        Panel(
            f"[bold]Tipo:[/]      {emoji} {mv_type}\n"
            f"[bold]Hipotese:[/]  {classification.get('primary_hypothesis', '?')}\n"
            f"[bold]Confianca:[/] {classification.get('confidence', '?')}\n"
            f"[bold]Delta indice:[/]  {classification.get('delta_index', 0):.2f}%\n"
            f"[bold]Delta setor:[/]   {classification.get('delta_sector', 0):.2f}%",
            title="[Classificacao]",
            border_style="yellow",
        )
    )

    console.print(
        Panel(
            str(explanation_text),
            title="[Explicacao do Agente]",
            border_style="magenta",
        )
    )

    if parsed:
        console.print("\n[bold green]Structured output - JSON valido retornado pelo agente[/]\n")
        pprint(parsed)
    else:
        console.print("\n[bold yellow]Fallback - resposta textual do LLM[/]\n")


def _try_parse_json(value: str) -> dict | None:
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def print_error(msg: str, error: Exception | None = None) -> None:
    """Exibe um erro fatal no terminal de forma amigavel."""
    console.print()
    err_text = f"\n[dim]{error}[/]" if error else ""
    console.print(
        Panel(
            f"[bold red]{msg}[/]{err_text}",
            title=" Erro na Execucao",
            border_style="red",
        )
    )
    console.print()
