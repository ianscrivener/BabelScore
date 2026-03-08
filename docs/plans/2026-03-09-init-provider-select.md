# /init Provider Select Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace free-text provider entry in `/init` with a `WordCompleter` dropdown from `config.json`, auto-fill base URL as an editable default, resolve API keys from env/`~/.babelscore/.env`, and prompt+save any missing keys.

**Architecture:** `write_env_key` handles `.env` I/O in `project.py`. `load_providers`, `_pick_provider`, and `_resolve_api_key` are added to `init_wizard.py`. `run_wizard` is updated to use these. `_resolve_api_key` returns `(raw_value, env_ref)` — raw value for the model fetch HTTP call, env ref for storage in `config.yaml`.

**Tech Stack:** Python 3.12, prompt_toolkit `WordCompleter` + `pt_prompt(default=...)`, PyYAML, existing httpx/Rich stack.

**Design doc:** `docs/plans/2026-03-09-init-provider-select-design.md`

---

### Task 1: write_env_key in project.py

**Files:**
- Modify: `babelscore/config/project.py`
- Modify: `tests/test_project.py`

**Step 1: Write the failing tests** (add to end of `tests/test_project.py`):

```python
def test_write_env_key_creates_file(tmp_path):
    with patch("babelscore.config.project.BABELSCORE_DIR", tmp_path):
        from babelscore.config.project import write_env_key
        write_env_key("OPENAI_API_KEY", "sk-abc123")
    env_path = tmp_path / ".env"
    assert env_path.exists()
    assert "OPENAI_API_KEY=sk-abc123" in env_path.read_text()


def test_write_env_key_appends_to_existing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("EXISTING_KEY=already-here\n")
    with patch("babelscore.config.project.BABELSCORE_DIR", tmp_path):
        from babelscore.config.project import write_env_key
        write_env_key("NEW_KEY", "new-value")
    content = env_path.read_text()
    assert "EXISTING_KEY=already-here" in content
    assert "NEW_KEY=new-value" in content


def test_write_env_key_creates_parent_dirs(tmp_path):
    nested = tmp_path / "nested"
    with patch("babelscore.config.project.BABELSCORE_DIR", nested):
        from babelscore.config.project import write_env_key
        write_env_key("FOO", "bar")
    assert (nested / ".env").exists()
```

**Step 2: Run to verify they fail:**

```bash
cd /Users/ianscrivener/zzCODE26zz/BabelScore && source .venv/bin/activate && pytest tests/test_project.py::test_write_env_key_creates_file tests/test_project.py::test_write_env_key_appends_to_existing tests/test_project.py::test_write_env_key_creates_parent_dirs -v
```

Expected: `ImportError: cannot import name 'write_env_key'`

**Step 3: Add write_env_key to `babelscore/config/project.py`:**

```python
def write_env_key(var_name: str, value: str) -> None:
    """Append VAR=value to ~/.babelscore/.env. Creates file and dirs if absent."""
    BABELSCORE_DIR.mkdir(parents=True, exist_ok=True)
    env_path = BABELSCORE_DIR / ".env"
    with env_path.open("a") as f:
        f.write(f"{var_name}={value}\n")
```

**Step 4: Run tests:**

```bash
pytest tests/test_project.py -v
```

Expected: all pass (8 total).

**Step 5: Commit:**

```bash
git add babelscore/config/project.py tests/test_project.py
git commit -m "feat: add write_env_key to project.py"
```

---

### Task 2: load_providers in init_wizard.py

**Files:**
- Modify: `babelscore/cli/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

**Step 1: Write the failing tests** (add to end of `tests/test_init_wizard.py`):

```python
from pathlib import Path
import json
from babelscore.cli.init_wizard import load_providers

def test_load_providers_custom_is_first():
    providers = load_providers()
    assert providers[0]["name"] == "Custom"


def test_load_providers_returns_all_config_providers():
    providers = load_providers()
    names = [p["name"] for p in providers]
    assert "OpenAI" in names
    assert "Anthropic" in names
    assert "Ollama" in names


def test_load_providers_fallback_on_bad_config(tmp_path):
    bad_config = tmp_path / "config.json"
    bad_config.write_text("not json")
    with patch("babelscore.cli.init_wizard._CONFIG_PATH", bad_config), \
         patch("babelscore.cli.init_wizard.console"):
        providers = load_providers()
    assert len(providers) == 1
    assert providers[0]["name"] == "Custom"
```

**Step 2: Run to verify they fail:**

```bash
pytest tests/test_init_wizard.py::test_load_providers_custom_is_first -v
```

Expected: `ImportError: cannot import name 'load_providers'`

**Step 3: Add to top of `babelscore/cli/init_wizard.py`** (after existing imports):

```python
import json
from pathlib import Path

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
```

**Step 4: Run tests:**

```bash
pytest tests/test_init_wizard.py -v
```

Expected: all pass (new + existing).

**Step 5: Commit:**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: add load_providers to init_wizard"
```

---

### Task 3: _pick_provider in init_wizard.py

**Files:**
- Modify: `babelscore/cli/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

**Step 1: Write the failing tests:**

```python
def test_pick_provider_returns_matching_provider():
    with patch("babelscore.cli.init_wizard.pt_prompt", return_value="OpenAI"):
        from babelscore.cli.init_wizard import _pick_provider
        result = _pick_provider("Translator")
    assert result["name"] == "OpenAI"
    assert result["base_url"] == "https://api.openai.com/v1"


def test_pick_provider_custom_returns_custom():
    with patch("babelscore.cli.init_wizard.pt_prompt", return_value="Custom"):
        from babelscore.cli.init_wizard import _pick_provider
        result = _pick_provider("Judge")
    assert result["name"] == "Custom"


def test_pick_provider_reprompts_on_unknown(capsys):
    # First call returns garbage, second returns valid
    with patch("babelscore.cli.init_wizard.pt_prompt", side_effect=["garbage", "Ollama"]), \
         patch("babelscore.cli.init_wizard.console"):
        from babelscore.cli.init_wizard import _pick_provider
        result = _pick_provider("Translator")
    assert result["name"] == "Ollama"
```

**Step 2: Run to verify they fail:**

```bash
pytest tests/test_init_wizard.py::test_pick_provider_returns_matching_provider -v
```

Expected: `ImportError: cannot import name '_pick_provider'`

**Step 3: Add imports and `_pick_provider` to `init_wizard.py`:**

Add to imports at top of file:
```python
from prompt_toolkit.completion import WordCompleter
```

Add function after `load_providers`:
```python
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
```

**Step 4: Run tests:**

```bash
pytest tests/test_init_wizard.py -v
```

Expected: all pass.

**Step 5: Commit:**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: add _pick_provider with WordCompleter dropdown"
```

---

### Task 4: _resolve_api_key in init_wizard.py

**Files:**
- Modify: `babelscore/cli/init_wizard.py`
- Modify: `tests/test_init_wizard.py`

**Context:** `_resolve_api_key(provider)` returns `(raw_value: str, env_ref: str)`.
- `raw_value` — the actual key string (used for HTTP calls like model fetch)
- `env_ref` — `${VAR_NAME}` reference (stored in config.yaml)
- For `key_reqd: false` providers (Ollama etc.), returns `("", "")`
- Lookup order: `os.environ` → `~/.babelscore/.env` → prompt (masked) → write to `.env`

**Step 1: Write the failing tests:**

```python
import os

def test_resolve_api_key_not_required_returns_empty():
    from babelscore.cli.init_wizard import _resolve_api_key
    val, ref = _resolve_api_key({"key_reqd": False, "api_key": ""})
    assert val == ""
    assert ref == ""


def test_resolve_api_key_found_in_env():
    provider = {"key_reqd": True, "api_key": "${OPENAI_API_KEY}"}
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-from-env"}):
        from babelscore.cli.init_wizard import _resolve_api_key
        val, ref = _resolve_api_key(provider)
    assert val == "sk-from-env"
    assert ref == "${OPENAI_API_KEY}"


def test_resolve_api_key_found_in_dot_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\n")
    provider = {"key_reqd": True, "api_key": "${OPENAI_API_KEY}"}
    with patch.dict(os.environ, {}, clear=False), \
         patch("babelscore.cli.init_wizard.BABELSCORE_DIR", tmp_path):
        # Ensure env var is NOT set
        os.environ.pop("OPENAI_API_KEY", None)
        from babelscore.cli.init_wizard import _resolve_api_key
        val, ref = _resolve_api_key(provider)
    assert val == "sk-from-file"
    assert ref == "${OPENAI_API_KEY}"


def test_resolve_api_key_prompts_and_saves_when_missing(tmp_path):
    provider = {"key_reqd": True, "api_key": "${OPENAI_API_KEY}"}
    with patch.dict(os.environ, {}, clear=False), \
         patch("babelscore.cli.init_wizard.BABELSCORE_DIR", tmp_path), \
         patch("babelscore.config.project.BABELSCORE_DIR", tmp_path), \
         patch("babelscore.cli.init_wizard.prompt", return_value="sk-entered"):
        os.environ.pop("OPENAI_API_KEY", None)
        from babelscore.cli.init_wizard import _resolve_api_key
        val, ref = _resolve_api_key(provider)
    assert val == "sk-entered"
    assert ref == "${OPENAI_API_KEY}"
    assert "OPENAI_API_KEY=sk-entered" in (tmp_path / ".env").read_text()


def test_resolve_api_key_reprompts_on_empty(tmp_path):
    provider = {"key_reqd": True, "api_key": "${MY_KEY}"}
    with patch.dict(os.environ, {}, clear=False), \
         patch("babelscore.cli.init_wizard.BABELSCORE_DIR", tmp_path), \
         patch("babelscore.config.project.BABELSCORE_DIR", tmp_path), \
         patch("babelscore.cli.init_wizard.prompt", side_effect=["", "sk-valid"]), \
         patch("babelscore.cli.init_wizard.console"):
        os.environ.pop("MY_KEY", None)
        from babelscore.cli.init_wizard import _resolve_api_key
        val, ref = _resolve_api_key(provider)
    assert val == "sk-valid"
```

**Step 2: Run to verify they fail:**

```bash
pytest tests/test_init_wizard.py::test_resolve_api_key_not_required_returns_empty -v
```

Expected: `ImportError`

**Step 3: Add imports and `_resolve_api_key` to `init_wizard.py`:**

Add to imports:
```python
import os
from babelscore.config.project import (
    create_project,
    project_exists,
    save_model_cache,
    write_env_key,
    BABELSCORE_DIR,
)
```

(Replace the existing import of `create_project, project_exists, save_model_cache`)

Add function after `_pick_provider`:
```python
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
```

**Step 4: Run tests:**

```bash
pytest tests/test_init_wizard.py -v
```

Expected: all pass.

**Step 5: Commit:**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: add _resolve_api_key with env lookup and .env write"
```

---

### Task 5: Wire into run_wizard

**Files:**
- Modify: `babelscore/cli/init_wizard.py`

**Step 1: No new tests** — existing `test_run_wizard_happy_path_creates_config` covers the output; update `_run_wizard_with` helper to also patch `_pick_provider` and `_resolve_api_key`.

Update `_run_wizard_with` in `tests/test_init_wizard.py`:

```python
def _run_wizard_with(inputs, tmp_path, *, fetch_return=None, extra_patches=None):
    """Run wizard with canned prompt responses; patches PROJECTS_DIR to tmp_path."""
    mock_provider = {
        "name": "Custom",
        "base_url": "",
        "api_key": "",
        "key_reqd": False,
        "notes": "",
    }
    patches = [
        patch("babelscore.cli.init_wizard.prompt", side_effect=list(inputs)),
        patch("babelscore.cli.init_wizard.fetch_models", return_value=fetch_return),
        patch("babelscore.cli.init_wizard.console"),
        patch("babelscore.cli.init_wizard._pick_provider", return_value=mock_provider),
        patch("babelscore.cli.init_wizard._resolve_api_key", return_value=("sk-test", "${CUSTOM_KEY}")),
        patch("babelscore.config.project.PROJECTS_DIR", tmp_path),
        patch("babelscore.config.project.BABELSCORE_DIR", tmp_path),
    ]
    if extra_patches:
        patches.extend(extra_patches)
    ctx = __import__("contextlib").ExitStack()
    mocks = [ctx.enter_context(p) for p in patches]
    with ctx:
        run_wizard()
    return mocks
```

Also update `_HAPPY_INPUTS` — the provider URL and key prompts are now gone for predefined providers, but Custom still prompts for URL. Since we're patching `_pick_provider` to return Custom with empty base_url, we still need the URL and model prompts:

```python
# _HAPPY_INPUTS stays the same — _pick_provider and _resolve_api_key are patched out
# The URL prompt (index 3,6) and key prompt (index 4,7) are bypassed by the patches
# But run_wizard now reads URL from provider dict or prompts for Custom
```

Actually, since `_pick_provider` is patched to return `Custom` (with empty base_url), `run_wizard` will prompt for the URL. So `_HAPPY_INPUTS` keeps its URL and model entries. Remove the key entries (indices 4 and 7) since `_resolve_api_key` is patched:

```python
_HAPPY_INPUTS = [
    "en-fr-test",                    # 0 project name
    "English",                       # 1 source lang
    "French",                        # 2 target lang
    "https://api.openai.com/v1",     # 3 translator URL (Custom path)
    "gpt-4o-mini",                   # 4 translator model
    "https://api.anthropic.com/v1",  # 5 judge URL (Custom path)
    "claude-sonnet-4-6",             # 6 judge model
    "y",                             # 7 show reasoning
    "n",                             # 8 flag variance
]
```

**Step 2: Replace translator and judge sections in `run_wizard`:**

Replace the current `# -- Translator model --` block with:

```python
        # -- Translator model --
        console.print("\n[cyan]── Translator model ──[/cyan]")
        t_provider = _pick_provider("Translator")
        if t_provider["name"] == "Custom":
            t_url = normalise_url(prompt("Base URL (e.g. https://api.openai.com/v1): ").strip())
        else:
            t_url_raw = pt_prompt("Base URL: ", default=t_provider["base_url"]).strip()
            t_url = normalise_url(t_url_raw if t_url_raw else t_provider["base_url"])
        t_val, t_key = _resolve_api_key(t_provider)
        t_model = _pick_model(t_url, t_val)
```

Replace the current `# -- Judge model --` block with:

```python
        # -- Judge model --
        console.print("\n[cyan]── Judge model ──[/cyan]")
        j_provider = _pick_provider("Judge")
        if j_provider["name"] == "Custom":
            j_url = normalise_url(prompt("Base URL: ").strip())
        else:
            j_url_raw = pt_prompt("Base URL: ", default=j_provider["base_url"]).strip()
            j_url = normalise_url(j_url_raw if j_url_raw else j_provider["base_url"])
        j_val, j_key = _resolve_api_key(j_provider)
        j_model = _pick_model(j_url, j_val)
```

Update config dict in `run_wizard` — `t_key` and `j_key` are now the env refs returned by `_resolve_api_key`:

```python
        config = {
            ...
            "translator_models": [
                {"name": t_model, "base_url": t_url, "api_key": t_key}
            ],
            "judge_models": [{"name": j_model, "base_url": j_url, "api_key": j_key}],
            ...
        }
```

**Step 3: Run full test suite:**

```bash
cd /Users/ianscrivener/zzCODE26zz/BabelScore && source .venv/bin/activate && pytest tests/ -v
```

Expected: all pass.

**Step 4: Commit:**

```bash
git add babelscore/cli/init_wizard.py tests/test_init_wizard.py
git commit -m "feat: wire provider select and key resolution into run_wizard"
```

---

### Task 6: Lint and final check

**Step 1: Run full test suite:**

```bash
pytest tests/ -v
```

Expected: all pass.

**Step 2: Lint and format:**

```bash
ruff check babelscore/ && ruff format babelscore/
```

**Step 3: Re-run tests after format:**

```bash
pytest tests/ -v 2>&1 | tail -5
```

**Step 4: Commit if any changes:**

```bash
git add -u && git diff --cached --stat
git commit -m "chore: ruff lint and format fixes"
```

**Step 5: Manual smoke test:**

```bash
source .venv/bin/activate && babelscore
```

Type `/init`. Verify:
- Provider dropdown appears with `Custom` at top and all providers listed
- Selecting OpenAI pre-fills the base URL
- If `OPENAI_API_KEY` is in env, shows "Using ${OPENAI_API_KEY} ✓"
- If not, prompts for value and writes to `~/.babelscore/.env`
