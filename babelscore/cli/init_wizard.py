import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import prompt as pt_prompt
from rich.console import Console
from rich.panel import Panel

from babelscore.config.project import (
    BABELSCORE_DIR,
    create_project,
    project_exists,
    save_model_cache,
    write_env_key,
)

console = Console()

_CONFIG_PATH = Path(__file__).parent / "config.json"

_CUSTOM_PROVIDER = {
    "name": "Custom",
    "base_url": "",
    "api_key": "",
    "key_reqd": False,
    "notes": "Enter your own base URL and API key.",
}


def load_providers() -> list[dict]:
    """Load provider list from config.json with Custom prepended."""
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        return [_CUSTOM_PROVIDER] + list(data["llms"].values())
    except Exception:
        console.print("[yellow]Warning: could not load config.json — using Custom only.[/yellow]")
        return [_CUSTOM_PROVIDER]


def _pick_provider(role: str) -> dict:
    """WordCompleter dropdown for provider selection. Re-prompts on invalid input."""
    providers = load_providers()
    name_map = {p["name"]: p for p in providers}
    completer = WordCompleter(list(name_map.keys()), match_middle=False)

    while True:
        raw = pt_prompt(
            f"{role} provider: ",
            completer=completer,
            complete_while_typing=True,
        ).strip()
        if raw in name_map:
            return name_map[raw]
        console.print(f"[yellow]Unknown provider '{raw}'. Pick from the dropdown.[/yellow]")


def _resolve_api_key(provider: dict) -> tuple[str, str]:
    """Return (raw_value, env_ref) for the provider's API key.

    Lookup: os.environ → ~/.babelscore/.env → prompt → write to .env
    Returns ("", "") for providers that don't require a key.
    """
    if not provider.get("key_reqd", False):
        return "", ""

    api_key_field = provider.get("api_key", "")
    var_name = api_key_field.strip("${}") if api_key_field.startswith("${") else api_key_field

    # 1. Check os.environ
    value = os.environ.get(var_name, "")

    # 2. Check ~/.babelscore/.env
    if not value:
        env_path = BABELSCORE_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{var_name}="):
                    value = line.split("=", 1)[1].strip()
                    break

    if value:
        console.print(f"[dim]Using ${{{var_name}}} ✓[/dim]")
        return value, f"${{{var_name}}}"

    # 3. Prompt and save
    while not value:
        value = prompt(f"Enter value for {var_name}: ", password=True).strip()
        if not value:
            console.print("[red]API key cannot be empty.[/red]")

    write_env_key(var_name, value)
    console.print(f"[dim]Saved {var_name} to ~/.babelscore/.env[/dim]")
    return value, f"${{{var_name}}}"


def normalise_url(url: str) -> str:
    """Prepend https:// if no protocol is present."""
    if url and not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def slug_from_url(base_url: str) -> str:
    """Extract hostname from base_url to use as provider cache key."""
    return urlparse(base_url).hostname or base_url


def fetch_models(base_url: str, api_key: str) -> list[str] | None:
    """Fetch model list from /v1/models. Returns list or None on any failure."""
    url = base_url.rstrip("/") + "/models"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0,
        )
    except Exception as exc:
        console.print(f"[red]Model fetch failed:[/red] {exc}")
        return None

    if response.status_code != 200:
        console.print(f"[red]Model fetch returned {response.status_code}[/red]")
        return None

    data = response.json().get("data", [])
    models = [m["id"] for m in data if "id" in m]
    if not models:
        console.print("[yellow]Provider returned no models.[/yellow]")
        return None

    return models


def prompt(message: str, *, password: bool = False) -> str:
    """Thin wrapper so tests can patch a single symbol."""
    return pt_prompt(message, is_password=password)


def _pick_model(base_url: str, api_key: str) -> str:
    """Fetch models with spinner, present numbered list, return chosen model name."""
    slug = slug_from_url(base_url)

    with console.status("[cyan]Fetching models\u2026[/cyan]"):
        models = fetch_models(base_url, api_key)

    if models:
        save_model_cache(slug, models)
        console.print("\n[cyan]Available models:[/cyan]")
        for i, m in enumerate(models, 1):
            console.print(f"  [dim]{i}.[/dim] {m}")
        raw = prompt("\nPick a number or type a model name: ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                return models[idx]
        return raw
    else:
        return prompt("Enter model name manually: ").strip()


def run_wizard():
    console.print(
        Panel(
            "Answer each prompt to set up your project.\n"
            "[dim]Press Ctrl+C at any time to cancel \u2014 nothing will be saved.[/dim]",
            title="/init \u2014 New Project",
            border_style="cyan",
        )
    )

    try:
        # -- Project metadata --
        name = prompt("Project name (slug, e.g. en-fr-test): ").strip()
        if not name:
            console.print("[red]Project name cannot be empty.[/red]")
            return

        if project_exists(name):
            console.print(f"[yellow]Project '{name}' already exists.[/yellow]")
            overwrite = prompt("Overwrite? [y/N]: ").strip().lower()
            if overwrite != "y":
                console.print("[dim]Init cancelled.[/dim]")
                return

        source_lang = prompt("Source language (e.g. English): ").strip()
        target_lang = prompt("Target language (e.g. French): ").strip()

        console.print(
            "[dim]Paradigm: 2 (one-way cold judge) \u2014 fixed for Phase 1[/dim]"
        )

        # -- Translator model --
        console.print("\n[cyan]-- Translator model --[/cyan]")
        t_url = normalise_url(prompt("Provider base URL (e.g. https://api.openai.com/v1): ").strip())
        t_key_raw = prompt("API key (or env var name, e.g. OPENAI_API_KEY): ").strip()
        t_key = f"${{{t_key_raw}}}" if not t_key_raw.startswith("${") else t_key_raw
        t_model = _pick_model(t_url, t_key_raw)

        # -- Judge model --
        console.print("\n[cyan]-- Judge model --[/cyan]")
        j_url = normalise_url(prompt("Provider base URL: ").strip())
        j_key_raw = prompt("API key (or env var name): ").strip()
        j_key = f"${{{j_key_raw}}}" if not j_key_raw.startswith("${") else j_key_raw
        j_model = _pick_model(j_url, j_key_raw)

        # -- Output options --
        console.print("\n[cyan]-- Output options --[/cyan]")
        show_reasoning = prompt("Show judge reasoning? [Y/n]: ").strip().lower()
        flag_variance = prompt("Flag high variance? [Y/n]: ").strip().lower()

        config = {
            "project": name,
            "paradigm": 2,
            "source_language": source_lang,
            "target_language": target_lang,
            "translator_models": [
                {"name": t_model, "base_url": t_url, "api_key": t_key}
            ],
            "judge_models": [{"name": j_model, "base_url": j_url, "api_key": j_key}],
            "output": {
                "format": "markdown",
                "show_judge_reasoning": show_reasoning != "n",
                "flag_high_variance": flag_variance != "n",
            },
        }

        proj_dir = create_project(config)

    except KeyboardInterrupt:
        console.print("\n[dim]Init cancelled. No files written.[/dim]")
        return

    console.print(
        Panel(
            f"[green]Project created:[/green] {proj_dir}\n\n"
            f"  Source: {source_lang} \u2192 {target_lang}\n"
            f"  Translator: {t_model}\n"
            f"  Judge:      {j_model}\n\n"
            f"[dim]Add source sentences to {proj_dir}/data/test_set.csv\n"
            f"Then run: babelscore run {name}[/dim]",
            title="Project created",
            border_style="green",
        )
    )
