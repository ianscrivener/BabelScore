# TUI Milestone 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Launch a Rich + prompt_toolkit interactive shell with a branded banner, `/init`, `/help`, `/exit` slash commands, and clean Ctrl+C exit.

**Architecture:** A Click entrypoint routes bare `babelscore` invocation to `shell.py`, which runs a prompt_toolkit REPL loop. Rich handles all output. Commands are dispatched via a plain dict.

**Tech Stack:** Python 3.12, Rich, prompt_toolkit, Click. No Textual.

---

## Task 1: Install dependencies

**Files:**
- Modify: `pyproject.toml` (via uv add — do not edit directly)

**Step 1: Install runtime deps**

```bash
source .venv/bin/activate
uv add rich prompt_toolkit click
```

Expected output: packages added, `pyproject.toml` and `uv.lock` updated.

**Step 2: Verify install**

```bash
python -c "import rich; import prompt_toolkit; import click; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add rich, prompt_toolkit, click dependencies"
```

---

## Task 2: Scaffold package structure

**Files:**
- Create: `babelscore/__init__.py`
- Create: `babelscore/cli/__init__.py`
- Create: `babelscore/cli/main.py`
- Create: `babelscore/cli/shell.py`

**Step 1: Create directories and empty init files**

```bash
mkdir -p babelscore/cli
touch babelscore/__init__.py
touch babelscore/cli/__init__.py
```

**Step 2: Create `babelscore/cli/main.py`**

```python
import click
from babelscore.cli.shell import run_shell


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """BabelScore — LLM translation quality benchmark."""
    if ctx.invoked_subcommand is None:
        run_shell()


def main():
    cli()
```

**Step 3: Create `babelscore/cli/shell.py` — skeleton only**

```python
def run_shell():
    pass
```

**Step 4: Add entrypoint to `pyproject.toml` via uv**

Add this to `pyproject.toml` under `[project.scripts]` — this one edit to pyproject.toml is structural, not a dependency, so it is done directly:

```toml
[project.scripts]
babelscore = "babelscore.cli.main:main"
```

Then reinstall:

```bash
uv pip install -e .
```

**Step 5: Verify entrypoint resolves**

```bash
babelscore --help
```

Expected: Shows Click help text with no errors.

**Step 6: Commit**

```bash
git add babelscore/ pyproject.toml
git commit -m "feat: scaffold babelscore package and click entrypoint"
```

---

## Task 3: Build the banner

**Files:**
- Modify: `babelscore/cli/shell.py`

**Step 1: Add banner function to `shell.py`**

```python
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
```

**Step 2: Call it from `run_shell`**

```python
def run_shell():
    print_banner()
```

**Step 3: Smoke test**

```bash
babelscore
```

Expected: Banner prints and process exits (no REPL yet).

**Step 4: Commit**

```bash
git add babelscore/cli/shell.py
git commit -m "feat: add babelscore ASCII banner"
```

---

## Task 4: Build the REPL loop with prompt_toolkit

**Files:**
- Modify: `babelscore/cli/shell.py`

**Step 1: Add REPL loop to `run_shell`**

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

PROMPT_STYLE = Style.from_dict({"prompt": "cyan bold"})

bindings = KeyBindings()

@bindings.add("escape")
def _escape(event):
    event.app.exit(exception=KeyboardInterrupt)


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
```

**Step 2: Add stub `dispatch` function**

```python
def dispatch(text: str):
    console.print(f"[yellow]Unknown command:[/yellow] {text}")
```

**Step 3: Test manually**

```bash
babelscore
```

Expected:
- Banner displays
- `> ` prompt appears
- Typing anything shows "Unknown command: ..."
- Ctrl+C prints `Goodbye.` and exits cleanly
- Escape exits cleanly

**Step 4: Commit**

```bash
git add babelscore/cli/shell.py
git commit -m "feat: add prompt_toolkit REPL loop with clean exit handling"
```

---

## Task 5: Implement slash command dispatch and handlers

**Files:**
- Modify: `babelscore/cli/shell.py`

**Step 1: Add command handlers**

```python
from rich.panel import Panel


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
        "[cyan]/exit[/cyan]    Exit BabelScore",
        title="Commands",
        border_style="dim",
    ))


def cmd_exit():
    raise KeyboardInterrupt
```

**Step 2: Replace stub `dispatch` with dict dispatch**

```python
COMMANDS = {
    "/init":  cmd_init,
    "/help":  cmd_help,
    "/exit":  cmd_exit,
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
```

**Step 3: Test all commands manually**

```bash
babelscore
```

Verify:
- `/init` shows the panel
- `/help` shows the command list
- `/exit` and `/quit` both exit cleanly
- Unknown command shows the error message
- Non-slash input shows the slash hint

**Step 4: Commit**

```bash
git add babelscore/cli/shell.py
git commit -m "feat: implement slash command dispatch — /init /help /exit"
```

---

## Task 6: Write tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_shell.py`

**Step 1: Install test deps**

```bash
uv add --dev pytest
```

**Step 2: Create `tests/__init__.py`**

```bash
mkdir -p tests
touch tests/__init__.py
```

**Step 3: Write tests for dispatch logic**

```python
# tests/test_shell.py
import pytest
from unittest.mock import patch, MagicMock
from babelscore.cli.shell import dispatch, COMMANDS


def test_dispatch_unknown_command_prints_error():
    with patch("babelscore.cli.shell.console") as mock_console:
        dispatch("/foobar")
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "Unknown command" in args


def test_dispatch_non_slash_input_prints_hint():
    with patch("babelscore.cli.shell.console") as mock_console:
        dispatch("hello")
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "/" in args


def test_dispatch_init_calls_cmd_init():
    with patch("babelscore.cli.shell.cmd_init") as mock_init:
        dispatch("/init")
        mock_init.assert_called_once()


def test_dispatch_exit_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        dispatch("/exit")


def test_dispatch_quit_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        dispatch("/quit")


def test_all_commands_registered():
    for cmd in ["/init", "/help", "/exit", "/quit"]:
        assert cmd in COMMANDS
```

**Step 4: Run tests**

```bash
pytest tests/test_shell.py -v
```

Expected: all 6 tests pass.

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: add dispatch unit tests for TUI shell"
```

---

## Done

Milestone 1 exit criteria:
- `babelscore` launches with branded banner
- `/init` shows stub panel
- `/help` lists commands
- `/exit`, `/quit`, Ctrl+C, Escape all exit cleanly with `Goodbye.`
- All dispatch tests pass
