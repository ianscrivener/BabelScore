from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

console = Console()

ASCII_LOGO = r"""
 ██████   █████  ██████  ███████ ██      ███████  ██████  ██████  ██████  ███████
 ██   ██ ██   ██ ██   ██ ██      ██      ██      ██      ██      ██    ██ ██
 ██████  ███████ ██████  █████   ██      ███████ ██      ██      ██    ██ █████
 ██   ██ ██   ██ ██   ██ ██      ██           ██ ██      ██      ██    ██ ██
 ██████  ██   ██ ██████  ███████ ███████ ███████  ██████  ██████  ██████  ███████
"""

VERSION = "0.1.0"

PROMPT_STYLE = Style.from_dict({"prompt": "cyan bold"})

bindings = KeyBindings()


@bindings.add("escape")
def _escape(event):
    event.app.exit(exception=KeyboardInterrupt)


def print_banner():
    logo = Text(ASCII_LOGO, style="bold cyan")
    console.print(logo)
    console.print(
        f"  Score the translation capability of any LLM.\n"
        f"  [dim]v{VERSION}  |  Type /help for commands  |  Ctrl+C to exit[/dim]\n"
    )


def cmd_init():
    console.print(Panel(
        "BabelScore project initialisation\n\n"
        "This command will guide you through creating a new\n"
        "evaluation project — language pair, translator models,\n"
        "judge models, and test data.\n\n"
        "[dim]Coming soon.[/dim]",
        title="/init",
        border_style="cyan",
    ))


def cmd_help():
    console.print(Panel(
        "[cyan]/init[/cyan]    Start a new evaluation project\n"
        "[cyan]/help[/cyan]    Show this help message\n"
        "[cyan]/quit[/cyan]    Exit BabelScore",
        title="Commands",
        border_style="dim",
    ))


def cmd_exit():
    raise KeyboardInterrupt


COMMANDS = {
    "/init":  cmd_init,
    "/help":  cmd_help,
    "/quit":  cmd_exit,
}


def dispatch(text: str):
    if not text.startswith("/"):
        console.print("[yellow]Commands start with /. Type /help for options.[/yellow]")
        return
    cmd = text.split()[0].lower()
    handler = COMMANDS.get(cmd)
    if handler:
        handler()
    else:
        console.print(f"[yellow]Unknown command:[/yellow] {cmd}  — type /help for available commands.")


def run_shell():
    print_banner()
    completer = WordCompleter(list(COMMANDS.keys()), match_middle=False)
    session = PromptSession(
        message=[("class:prompt", "> ")],
        style=PROMPT_STYLE,
        key_bindings=bindings,
        completer=completer,
        complete_while_typing=True,
    )
    while True:
        try:
            raw = session.prompt()
            text = raw.strip()
            if not text:
                continue
            dispatch(text)
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/dim]")
            break
        except EOFError:
            console.print("\n[dim]Goodbye.[/dim]")
            break
