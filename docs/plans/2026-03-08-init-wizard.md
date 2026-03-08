# /init Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the `/init` TUI wizard that walks the user through creating a BabelScore project via sequential prompts, fetches available models from the provider's `/v1/models` endpoint, and writes `config.yaml` + directory structure to `~/.babelscore/projects/[name]/`.

**Architecture:** `init_wizard.py` owns all prompt logic and model fetching; `project.py` owns file I/O (creating dirs and writing YAML + model cache). `shell.py` delegates `cmd_init()` to `run_wizard()`. Nothing is written until all prompts complete — Ctrl+C is always clean.

**Tech Stack:** Python 3.12, httpx (async HTTP), PyYAML (config write), prompt_toolkit (masked input, prompts), Rich (spinner, panels), pytest.

**Design doc:** `docs/plans/2026-03-08-init-wizard-design.md`

---

### Task 1: Add dependencies

**Files:**
- Modify: `pyproject.toml` (via uv add)

**Step 1: Add httpx and pyyaml**

```bash
source .venv/bin/activate
uv add httpx pyyaml
```

Expected: both appear in `pyproject.toml` dependencies.

**Step 2: Verify**

```bash
python -c "import httpx, yaml; print('ok')"
```

Expected: `ok`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add httpx and pyyaml dependencies"
```

---

### Task 2: project.py — create directory structure and write config.yaml

**Files:**
- Create: `babelscore/config/project.py`
- Create: `tests/test_project.py`

**Step 1: Write the failing tests**

Create `tests/test_project.py`:

```python
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
from babelscore.config.project import create_project, project_exists


SAMPLE_CONFIG = {
    "project": "test-proj",
    "paradigm": 2,
    "source_language": "English",
    "target_language": "French",
    "translator_models": [
        {"name": "gpt-4o-mini", "base_url": "https://api.openai.com/v1", "api_key": "${OPENAI_API_KEY}"}
    ],
    "judge_models": [
        {"name": "claude-sonnet-4-6", "base_url": "https://api.anthropic.com/v1", "api_key": "${ANTHROPIC_API_KEY}"}
    ],
    "output": {
        "format": "markdown",
        "show_judge_reasoning": True,
        "flag_high_variance": True,
    },
}


def test_create_project_creates_dirs(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        create_project(SAMPLE_CONFIG)
    proj_dir = tmp_path / "test-proj"
    assert (proj_dir / "data").is_dir()
    assert (proj_dir / "results").is_dir()


def test_create_project_writes_config_yaml(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        create_project(SAMPLE_CONFIG)
    config_path = tmp_path / "test-proj" / "config.yaml"
    assert config_path.exists()
    loaded = yaml.safe_load(config_path.read_text())
    assert loaded["project"] == "test-proj"
    assert loaded["source_language"] == "English"


def test_project_exists_true(tmp_path):
    (tmp_path / "existing-proj").mkdir()
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        assert project_exists("existing-proj") is True


def test_project_exists_false(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        assert project_exists("no-such-proj") is False
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_project.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `project.py` doesn't exist yet.

**Step 3: Create `babelscore/config/__init__.py`** (if not present)

```bash
touch babelscore/config/__init__.py
```

**Step 4: Write minimal implementation**

Create `babelscore/config/project.py`:

```python
from pathlib import Path
import yaml

BABELSCORE_DIR = Path.home() / ".babelscore"
PROJECTS_DIR = BABELSCORE_DIR / "projects"


def project_exists(name: str) -> bool:
    return (PROJECTS_DIR / name).exists()


def create_project(config: dict) -> Path:
    """Write config.yaml and create data/ results/ dirs. Returns project path."""
    name = config["project"]
    proj_dir = PROJECTS_DIR / name
    (proj_dir / "data").mkdir(parents=True, exist_ok=True)
    (proj_dir / "results").mkdir(parents=True, exist_ok=True)

    config_path = proj_dir / "config.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    return proj_dir
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_project.py -v
```

Expected: 4 passed.

**Step 6: Commit**

```bash
git add babelscore/config/__init__.py babelscore/config/project.py tests/test_project.py
git commit -m "feat: add project.py — create dirs and write config.yaml"
```

---

### Task 3: project.py — model cache

**Files:**
- Modify: `babelscore/config/project.py`
- Modify: `tests/test_project.py`

**Step 1: Write the failing test** (add to `tests/test_project.py`):

```python
import json

def test_save_model_cache_writes_json(tmp_path):
    with patch("babelscore.config.project.BABELSCORE_DIR", tmp_path):
        from babelscore.config.project import save_model_cache
        save_model_cache("api.openai.com", ["gpt-4o", "gpt-4o-mini"])
    cache_path = tmp_path / "providers" / "api.openai.com" / "models.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert "gpt-4o" in data
```

**Step 2: Run to verify it fails**

```bash
pytest tests/test_project.py::test_save_model_cache_writes_json -v
```

Expected: `ImportError`

**Step 3: Add `save_model_cache` to `project.py`**

```python
import json

def save_model_cache(provider_slug: str, models: list[str]) -> None:
    """Cache model list for a provider."""
    cache_dir = BABELSCORE_DIR / "providers" / provider_slug
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "models.json").write_text(json.dumps(models, indent=2))
```

**Step 4: Run tests**

```bash
pytest tests/test_project.py -v
```

Expected: 5 passed.

**Step 5: Commit**

```bash
git add babelscore/config/project.py tests/test_project.py
git commit -m "feat: add save_model_cache to project.py"
```

---

### Task 4: init_wizard.py — model fetch

**Files:**
- Create: `babelscore/cli/init_wizard.py`
- Create: `tests/test_init_wizard.py`

**Step 1: Write the failing tests**

Create `tests/test_init_wizard.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from babelscore.cli.init_wizard import fetch_models, slug_from_url


def test_slug_from_url_strips_protocol():
    assert slug_from_url("https://api.openai.com/v1") == "api.openai.com"


def test_slug_from_url_localhost():
    assert slug_from_url("http://localhost:11434/v1") == "localhost"


def test_fetch_models_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]
    }
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models == ["gpt-4o", "gpt-4o-mini"]


def test_fetch_models_http_error_returns_none():
    with patch("babelscore.cli.init_wizard.httpx.get", side_effect=Exception("timeout")):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None


def test_fetch_models_bad_status_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 401
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None


def test_fetch_models_empty_data_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_init_wizard.py -v
```

Expected: `ModuleNotFoundError`

**Step 3: Write `init_wizard.py` with fetch_models and slug_from_url**

Create `babelscore/cli/init_wizard.py`:

```python
from urllib.parse import urlparse
import httpx
from rich.console import Console

console = Console()


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
```

**Step 4: Run tests**

```bash
pytest tests/test_init_wizard.py -v
```

Expected: 6 passed.

**Step 5: Commit**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: add fetch_models and slug_from_url to init_wizard"
```

---

### Task 5: init_wizard.py — full prompt flow (run_wizard)

**Files:**
- Modify: `babelscore/cli/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

**Step 1: Write the failing tests** (add to `tests/test_init_wizard.py`):

```python
from unittest.mock import call

def test_run_wizard_cancelled_writes_nothing(tmp_path):
    """Ctrl+C during wizard must not create any files."""
    inputs = iter(["my-proj"])  # KeyboardInterrupt on first real prompt
    with patch("babelscore.cli.init_wizard.prompt", side_effect=KeyboardInterrupt), \
         patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        from babelscore.cli.init_wizard import run_wizard
        run_wizard()
    assert list(tmp_path.iterdir()) == []


def test_run_wizard_existing_project_warns(tmp_path):
    """If project already exists, wizard warns before proceeding."""
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path), \
         patch("babelscore.cli.init_wizard.project_exists", return_value=True), \
         patch("babelscore.cli.init_wizard.prompt", side_effect=KeyboardInterrupt), \
         patch("babelscore.cli.init_wizard.console") as mock_console:
        from babelscore.cli.init_wizard import run_wizard
        run_wizard()
    printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "already exists" in printed.lower() or "exist" in printed.lower()
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_init_wizard.py::test_run_wizard_cancelled_writes_nothing tests/test_init_wizard.py::test_run_wizard_existing_project_warns -v
```

Expected: `ImportError` for `run_wizard`

**Step 3: Add `run_wizard` to `init_wizard.py`**

Append to `babelscore/cli/init_wizard.py`:

```python
from prompt_toolkit.shortcuts import prompt as pt_prompt
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from babelscore.config.project import create_project, project_exists, save_model_cache


def prompt(message: str, *, password: bool = False) -> str:
    """Thin wrapper so tests can patch a single symbol."""
    return pt_prompt(message, is_password=password)


def _pick_model(base_url: str, api_key: str) -> str:
    """Fetch models with spinner, present numbered list, return chosen model name."""
    slug = slug_from_url(base_url)
    models = None

    with console.status("[cyan]Fetching models…[/cyan]"):
        models = fetch_models(base_url, api_key)

    if models:
        save_model_cache(slug, models)
        console.print("\n[cyan]Available models:[/cyan]")
        for i, m in enumerate(models, 1):
            console.print(f"  [dim]{i}.[/dim] {m}")
        raw = prompt("\nPick a number or type a model name: ")
        raw = raw.strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                return models[idx]
        return raw  # treat as literal model name
    else:
        return prompt("Enter model name manually: ").strip()


def run_wizard():
    console.print(Panel(
        "Answer each prompt to set up your project.\n"
        "[dim]Press Ctrl+C at any time to cancel — nothing will be saved.[/dim]",
        title="/init — New Project",
        border_style="cyan",
    ))

    try:
        # ── Project metadata ───────────────────────────────────────────────
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

        console.print("[dim]Paradigm: 2 (one-way cold judge) — fixed for Phase 1[/dim]")

        # ── Translator model ───────────────────────────────────────────────
        console.print("\n[cyan]── Translator model ──[/cyan]")
        t_url = prompt("Provider base URL (e.g. https://api.openai.com/v1): ").strip()
        t_key_raw = prompt("API key (or env var name, e.g. OPENAI_API_KEY): ").strip()
        t_key = f"${{{t_key_raw}}}" if not t_key_raw.startswith("${") else t_key_raw
        t_model = _pick_model(t_url, t_key_raw)

        # ── Judge model ────────────────────────────────────────────────────
        console.print("\n[cyan]── Judge model ──[/cyan]")
        j_url = prompt("Provider base URL: ").strip()
        j_key_raw = prompt("API key (or env var name): ").strip()
        j_key = f"${{{j_key_raw}}}" if not j_key_raw.startswith("${") else j_key_raw
        j_model = _pick_model(j_url, j_key_raw)

        # ── Output options ─────────────────────────────────────────────────
        console.print("\n[cyan]── Output options ──[/cyan]")
        show_reasoning = prompt("Show judge reasoning? [Y/n]: ").strip().lower()
        flag_variance  = prompt("Flag high variance? [Y/n]: ").strip().lower()

        config = {
            "project": name,
            "paradigm": 2,
            "source_language": source_lang,
            "target_language": target_lang,
            "translator_models": [
                {"name": t_model, "base_url": t_url, "api_key": t_key}
            ],
            "judge_models": [
                {"name": j_model, "base_url": j_url, "api_key": j_key}
            ],
            "output": {
                "format": "markdown",
                "show_judge_reasoning": show_reasoning != "n",
                "flag_high_variance":  flag_variance != "n",
            },
        }

        proj_dir = create_project(config)

    except KeyboardInterrupt:
        console.print("\n[dim]Init cancelled. No files written.[/dim]")
        return

    console.print(Panel(
        f"[green]Project created:[/green] {proj_dir}\n\n"
        f"  Source: {source_lang} → {target_lang}\n"
        f"  Translator: {t_model}\n"
        f"  Judge:      {j_model}\n\n"
        f"[dim]Add source sentences to {proj_dir}/data/test_set.csv\n"
        f"Then run: babelscore run {name}[/dim]",
        title="Project created",
        border_style="green",
    ))
```

**Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: all pass (including the 5 original shell tests).

**Step 5: Commit**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: implement run_wizard — full /init prompt flow"
```

---

### Task 6: Wire shell.py → run_wizard

**Files:**
- Modify: `babelscore/cli/shell.py`

**Step 1: No new test needed** — existing `test_dispatch_init_calls_cmd_init` already verifies dispatch; `run_wizard` is tested separately.

**Step 2: Update `cmd_init` in `shell.py`**

Replace the existing `cmd_init` function:

```python
from babelscore.cli.init_wizard import run_wizard

def cmd_init():
    run_wizard()
```

Remove the old Panel("Coming soon") body.

**Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 4: Smoke test manually**

```bash
source .venv/bin/activate
babelscore
```

Type `/init` and walk through the prompts. Ctrl+C should print "Init cancelled." and return to the shell.

**Step 5: Commit**

```bash
git add babelscore/cli/shell.py
git commit -m "feat: wire /init to run_wizard"
```

---

### Task 7: Final check

**Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 2: Run linter**

```bash
ruff check babelscore/
```

Fix any issues, then:

```bash
ruff format babelscore/
```

**Step 3: Commit if any lint fixes**

```bash
git add -u
git commit -m "chore: ruff lint fixes"
```

**Step 4: Manual end-to-end smoke test**

```bash
babelscore
```

- Run `/init`, complete all prompts with real values
- Verify `~/.babelscore/projects/[name]/config.yaml` exists and looks correct
- Verify `~/.babelscore/providers/[slug]/models.json` exists if fetch succeeded
- Run `/quit` to exit cleanly
