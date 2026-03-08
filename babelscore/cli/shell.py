from rich.console import Console
from rich.text import Text

console = Console()

ASCII_LOGO = r"""
 ██████   █████  ██████  ███████ ██      ███████  ██████  ██████  ██████  ███████
 ██   ██ ██   ██ ██   ██ ██      ██      ██      ██      ██      ██    ██ ██
 ██████  ███████ ██████  █████   ██      ███████ ██      ██      ██    ██ █████
 ██   ██ ██   ██ ██   ██ ██      ██           ██ ██      ██      ██    ██ ██
 ██████  ██   ██ ██████  ███████ ███████ ███████  ██████  ██████  ██████  ███████
"""

VERSION = "0.1.0"


def print_banner():
    logo = Text(ASCII_LOGO, style="bold cyan")
    console.print(logo)
    console.print(
        f"  Score the translation capability of any LLM.\n"
        f"  [dim]v{VERSION}  |  Type /help for commands  |  Ctrl+C to exit[/dim]\n"
    )


def run_shell():
    print_banner()
