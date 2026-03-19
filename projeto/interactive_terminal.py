import json
from dataclasses import dataclass
from typing import Any

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from projeto.display import console
from projeto.interactive_models import ModelOption, describe_current_model


@dataclass(frozen=True, slots=True)
class SlashCommand:
    name: str
    argument: str = ""


class InteractiveTerminal:
    def clear(self) -> None:
        console.clear()

    def prompt(self, *, provider: str | None, model: str | None) -> str:
        descriptor = describe_current_model(model or "sem-modelo", provider or "sem-provider")
        return Prompt.ask(f"[bold cyan]mercado[/] [dim]{descriptor}[/]").strip()

    def render_welcome(
        self,
        *,
        provider: str,
        model: str,
        checkpoint_label: str,
        thread_id: str,
    ) -> None:
        console.print()
        console.print(
            Panel(
                "[bold cyan]Terminal Financeiro[/]\n"
                "Converse sobre ativos, compare empresas e troque o modelo sem sair da sessao.\n"
                "[dim]Comandos: /help, /model, /status, /clear, /exit[/]",
                title=" Chat Interativo ",
                border_style="cyan",
            )
        )
        self.render_status(
            provider=provider,
            model=model,
            checkpoint_label=checkpoint_label,
            thread_id=thread_id,
        )

    def render_status(
        self,
        *,
        provider: str,
        model: str,
        checkpoint_label: str,
        thread_id: str,
    ) -> None:
        console.print(
            Panel(
                f"[bold]Modelo ativo:[/] {model}\n"
                f"[bold]Provider:[/] {provider}\n"
                f"[bold]Checkpoint:[/] {checkpoint_label}\n"
                f"[bold]Thread:[/] {thread_id}",
                title=" Sessao ",
                border_style="blue",
            )
        )

    def render_help(self) -> None:
        console.print(
            Panel(
                "/model            abre o seletor de modelos\n"
                "/model 3          troca pelo item 3 do catalogo\n"
                "/model gemini     vai para o padrao Gemini\n"
                "/model openrouter openai/gpt-4o-mini\n"
                "/status           mostra a configuracao atual\n"
                "/clear            limpa a tela\n"
                "/exit             encerra a sessao",
                title=" Comandos ",
                border_style="magenta",
            )
        )

    def render_model_catalog(
        self,
        options: list[ModelOption],
        *,
        current_provider: str | None,
        current_model: str | None,
    ) -> None:
        table = Table(
            title="Modelos disponiveis",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="bold cyan", no_wrap=True)
        table.add_column("Provider", style="bold")
        table.add_column("Modelo")
        table.add_column("Perfil")
        table.add_column("Status", no_wrap=True)
        table.add_column("Atual", no_wrap=True)

        for option in options:
            status = "OK" if option.provider_ready else "Configurar chave"
            current = "ATIVO" if (
                option.provider == current_provider and option.model == current_model
            ) else ""
            profile = option.description or ("Padrao" if option.is_default else "")
            table.add_row(
                str(option.index),
                option.provider_label,
                option.model,
                profile,
                status,
                current,
            )

        console.print(table)
        console.print(
            "[dim]Use /model <numero>, /model provider:model ou pressione ENTER para cancelar.[/]"
        )

    def prompt_model_selection(self) -> str:
        return Prompt.ask(
            "[bold cyan]Novo modelo[/] [dim](numero, provider:model ou ENTER cancela)[/]",
            default="",
        ).strip()

    def render_model_changed(self, *, provider: str, model: str) -> None:
        console.print(
            Panel(
                f"[bold green]Modelo atualizado[/]\n{describe_current_model(model, provider)}",
                title=" Runtime ",
                border_style="green",
            )
        )

    def render_tool_calls(self, names: list[str]) -> None:
        console.print(
            Panel(
                ", ".join(names),
                title=" Ferramentas em uso ",
                border_style="yellow",
            )
        )

    def render_tool_result(self, *, name: str | None, content: Any) -> None:
        parsed = _try_parse_json(content)
        if isinstance(parsed, dict) and parsed.get("erro"):
            self.render_error("A ferramenta retornou um erro.", parsed.get("erro"))
            return

        label = name or "tool"
        console.print(f"[dim]Ferramenta concluida:[/] {label}")

    def render_assistant(self, text: str, *, provider: str, model: str) -> None:
        renderable = _render_content(text)
        console.print(
            Panel(
                renderable,
                title=f" Assistente | {provider} ",
                subtitle=model,
                border_style="bright_blue",
            )
        )
        console.print()

    def render_info(self, message: str) -> None:
        console.print(Panel(message, title=" Info ", border_style="cyan"))

    def render_warning(self, message: str) -> None:
        console.print(Panel(message, title=" Aviso ", border_style="yellow"))

    def render_error(self, message: str, error: Any | None = None) -> None:
        details = f"\n[dim]{error}[/]" if error else ""
        console.print(Panel(f"[bold red]{message}[/]{details}", title=" Erro ", border_style="red"))


def parse_command(text: str) -> SlashCommand | None:
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None

    body = raw[1:].strip()
    if not body:
        return SlashCommand(name="help")

    name, _, argument = body.partition(" ")
    return SlashCommand(name=name.lower(), argument=argument.strip())


def _render_content(text: str) -> Any:
    parsed = _try_parse_json(text)
    if parsed is not None:
        return Syntax(
            json.dumps(parsed, ensure_ascii=False, indent=2),
            "json",
            word_wrap=True,
            line_numbers=False,
        )

    return Markdown(text)


def _try_parse_json(value: Any) -> dict[str, Any] | list[Any] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None
