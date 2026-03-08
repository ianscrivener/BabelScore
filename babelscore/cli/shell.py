from rich.console import Console
from rich.text import Text
from prompt_toolkit import PromptSession
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


def dispatch(text: str):
    console.print(f"[yellow]Unknown command:[/yellow] {text}")


def run_shell():
    print_banner()
    session = PromptSession(
        message=[("class:prompt", "> ")],
        style=PROMPT_STYLE,
        key_bindings=bindings,
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
