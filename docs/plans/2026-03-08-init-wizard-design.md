# /init Wizard — Design

**Date:** 2026-03-08
**Status:** Approved

## Summary

Implement the `/init` TUI wizard as a sequential prompt flow using prompt_toolkit and Rich. Creates a BabelScore project config at `~/.babelscore/projects/[name]/` by walking the user through project settings, language pair, and one translator + one judge model. Fetches available models from the provider's `/v1/models` endpoint with graceful manual fallback.

---

## Decisions

| Question | Decision |
|---|---|
| UX model | Sequential prompts with Rich spinner (no full-screen TUI) |
| Model fetch failure | Fail gracefully — show error, fall back to manual model name entry |
| Test data creation | Config + directories only — no sample CSV |
| Models per role | One translator, one judge (Phase 1 constraint) |
| Architecture | Dedicated `init_wizard.py` module; shell.py delegates |

---

## Flow

```
/init
  └─ Project name?          (slug format, not already exists)
  └─ Source language?       (free text)
  └─ Target language?       (free text)
  └─ Paradigm               (fixed: 2 — shown as info, not prompted)

  ── Translator model ──
  └─ Provider base URL?     (e.g. https://api.openai.com/v1)
  └─ API key?               (masked input)
  └─ [spinner] Fetching models from /v1/models...
       ✓ success → numbered list → user picks
       ✗ fail    → show error → "Enter model name manually:"

  ── Judge model ──
  └─ (same 4 steps as translator)

  ── Output options ──
  └─ Show judge reasoning?  (default: yes)
  └─ Flag high variance?    (default: yes)

  ── Write ──
  └─ Creates ~/.babelscore/projects/[name]/{config.yaml, data/, results/}
  └─ Caches model list → ~/.babelscore/providers/[slug]/models.json
  └─ Prints success summary panel
```

---

## Files

```
babelscore/
├── cli/
│   ├── shell.py          # cmd_init() → run_wizard()
│   └── init_wizard.py    # NEW — all wizard logic
└── config/
    └── project.py        # NEW — create_project(config) writes files/dirs

tests/
└── test_init_wizard.py   # NEW — unit tests for wizard steps
```

### Responsibilities

**`init_wizard.py`**
- Step-by-step prompt loop via prompt_toolkit
- Async model fetch + local cache (httpx, 5s timeout)
- Masked API key input (`is_password=True`)
- Graceful fallback to manual model name entry
- Calls `project.py` to write files only after all prompts complete

**`project.py`**
- Creates `~/.babelscore/projects/[name]/` directory tree (`data/`, `results/`)
- Writes `config.yaml` via PyYAML
- Writes model cache to `~/.babelscore/providers/[slug]/models.json`

**`shell.py`** change
```python
from babelscore.cli.init_wizard import run_wizard
def cmd_init():
    run_wizard()
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Project name already exists | Warn + ask to overwrite or pick new name |
| `/v1/models` timeout (5s) | Show error, fall through to manual model entry |
| `/v1/models` 401/403 | Show "invalid API key" message, fall through to manual |
| `/v1/models` returns empty list | Show warning, fall through to manual |
| Ctrl+C during wizard | Print "Init cancelled. No files written." — nothing created |
| `~/.babelscore/` doesn't exist yet | Create it silently |

**Key constraint:** nothing is written until all prompts are complete. Ctrl+C at any step leaves no files behind.

---

## Supported Providers

All providers use OpenAI-compatible `/v1/models` and `/v1/chat/completions`:

| Provider | Base URL example |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| Anthropic | via compatible wrapper |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Ollama | `http://localhost:11434/v1` |
| Together | `https://api.together.xyz/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| LiteLLM | `http://localhost:4000/v1` |
| LM Studio | `http://localhost:1234/v1` |
| Eden AI | via compatible endpoint |
| Portkey | `https://api.portkey.ai/v1` |
| AWS Bedrock | via LiteLLM proxy |
| Azure OpenAI | `https://[resource].openai.azure.com/openai/deployments/[deploy]/` |

Model slug for cache filename derived from base URL hostname (e.g. `api.openai.com` → `openai`).

---

## Config Output

```yaml
project: my-project
paradigm: 2
source_language: English
target_language: French

translator_models:
  - name: gpt-4o-mini
    base_url: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}

judge_models:
  - name: claude-sonnet-4-6
    base_url: https://api.anthropic.com/v1
    api_key: ${ANTHROPIC_API_KEY}

output:
  format: markdown
  show_judge_reasoning: true
  flag_high_variance: true
```

API keys are stored as env var references (`${VAR_NAME}`) in config.yaml — never as literal strings.
