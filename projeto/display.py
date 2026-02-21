"""
Módulo de exibição visual (UI) para o Agente de Atribuição de Movimento.

Desacopla a formatação do terminal (usando Rich) da lógica principal do entrypoint.
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
    "fetch_index_data": "Buscando dados do índice...",
    "fetch_sector_data": "Buscando dados do setor...",
    "fetch_news": "Buscando notícias...",
    "compute_metrics": "Calculando métricas...",
    "classify_movement": "Classificando movimento...",
    "generate_explanation": "[LLM] Gerando explicação [LLM]",
}


def print_agent_start(ticker: str, date: str, model: str, provider: str) -> None:
    """Exibe o cabeçalho inicial da execução do agente."""
    console.print(Panel(
        f"[bold cyan]Ticker:[/] {ticker}\n"
        f"[bold cyan]Data:[/] {date}\n"
        f"[bold cyan]Modelo:[/] {model}\n"
        f"[bold cyan]Provider:[/] {provider}",
        title=" Agente de Atribuição de Movimento V1 ",
        border_style="cyan",
    ))
    console.print()


def print_node_progress(node_name: str) -> None:
    """Exibe o progresso de um nó recém-concluído no stream do grafo."""
    label = _NODE_LABELS.get(node_name, f"{node_name}")
    console.print(f"  [dim]{label}[/] [green]OK[/]")


def display_result(result: dict) -> None:
    """Exibe o resultado final formatado no terminal."""
    console.print()
    
    metrics = result.get("metrics", {})
    classification = result.get("classification", {})
    explanation = result.get("explanation", "")

    console.print(Panel(
        f"[bold]Variação do ativo:[/]  {metrics.get('price_change_pct', 0):.2f}%\n"
        f"[bold]Variação do índice:[/] {metrics.get('index_change_pct', 0):.2f}%\n"
        f"[bold]Variação do setor:[/]  {metrics.get('sector_change_pct', 0):.2f}%\n"
        f"[bold]Volume ratio:[/]       {metrics.get('volume_ratio', 0):.2f}x\n"
        f"[bold]Anomalia de volume:[/] {'SIM' if metrics.get('volume_anomaly') else 'Não'}\n"
        f"[bold]Tendência mercado:[/]  {metrics.get('market_trend', '?')}",
        title="Métricas",
        border_style="green",
    ))

    mv_type = classification.get("movement_type", "?")
    emoji = _TYPE_EMOJI.get(mv_type, "?")

    console.print(Panel(
        f"[bold]Tipo:[/]      {emoji} {mv_type}\n"
        f"[bold]Hipótese:[/]  {classification.get('primary_hypothesis', '?')}\n"
        f"[bold]Confiança:[/] {classification.get('confidence', '?')}\n"
        f"[bold]Δ índice:[/]  {classification.get('delta_index', 0):.2f}%\n"
        f"[bold]Δ setor:[/]   {classification.get('delta_sector', 0):.2f}%",
        title="[Classificação]",
        border_style="yellow",
    ))

    console.print(Panel(
        explanation,
        title="[Explicação do Agente]",
        border_style="magenta",
    ))

    # Tentar parsear como JSON
    try:
        parsed = json.loads(explanation)
        console.print("\n[bold green] Structured output — JSON válido retornado pelo LLM[/]\n")
        pprint(parsed)
    except (json.JSONDecodeError, TypeError):
        console.print("\n[bold yellow] Fallback — resposta textual do LLM[/]\n")

def print_error(msg: str, error: Exception | None = None) -> None:
    """Exibe um erro fatal no terminal de forma amigável."""
    console.print()
    err_text = f"\n[dim]{error}[/]" if error else ""
    console.print(Panel(
        f"[bold red]{msg}[/]{err_text}",
        title=" Erro na Execução",
        border_style="red",
    ))
    console.print()
