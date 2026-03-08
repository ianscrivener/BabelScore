# /init Provider Select — Design

**Date:** 2026-03-09
**Status:** Approved

## Summary

Replace free-text provider entry in `/init` with a `WordCompleter` dropdown (same mechanism as slash command autocomplete) pre-populated from `babelscore/cli/config.json`. Auto-fill base URL as an editable default. Resolve API keys from env / `~/.babelscore/.env` before prompting; write new keys to `~/.babelscore/.env`.

---

## Decisions

| Question | Decision |
|---|---|
| Data sources | Skipped — focus on LLM provider select only |
| UI mechanism | `WordCompleter` dropdown (prompt_toolkit — no new dep) |
| Base URL | Pre-filled as editable default (user can confirm or change) |
| API key storage | Single `~/.babelscore/.env`; append if key not found |
| Key lookup order | env var → `~/.babelscore/.env` → prompt |

---

## Flow

```
Translator (and Judge) section:

1. "Select a provider:" → WordCompleter dropdown
     Custom / Ollama / LM Studio / OpenAI / Anthropic / ...
     (Custom always first; rest from config.json)

2a. Custom:
     → prompt base URL (free text, normalised)
     → prompt API key env var name + value
     → append VAR=value to ~/.babelscore/.env

2b. Predefined (e.g. OpenAI):
     → show pre-filled URL as editable default (user can edit)
     → resolve key: env var → ~/.babelscore/.env
         found:     show "Using ${OPENAI_API_KEY} ✓" — skip prompt
         not found: prompt value → append to ~/.babelscore/.env

3. Fetch models from /v1/models → numbered pick list or manual fallback
   (unchanged from current implementation)
```

---

## Files

```
babelscore/
├── cli/
│   ├── config.json         # add missing providers (OpenRouter, Groq, Together, LiteLLM, Portkey, Azure)
│   └── init_wizard.py      # add load_providers(), _pick_provider(), _resolve_api_key()
└── config/
    └── project.py          # add write_env_key(var_name, value)

~/.babelscore/
└── .env                    # read + appended to by wizard (created if absent)
```

### New functions

**`init_wizard.py`**

- `load_providers() -> list[dict]` — reads `config.json`, returns list with `{"name": "Custom", ...}` prepended
- `_pick_provider(role: str) -> dict` — renders WordCompleter prompt labelled "Translator provider:" or "Judge provider:"; returns selected provider dict
- `_resolve_api_key(provider: dict) -> str` — looks up key in env then `.env`; prompts + appends to `.env` if missing; returns env var reference string e.g. `${OPENAI_API_KEY}`

**`project.py`**

- `write_env_key(var_name: str, value: str) -> None` — appends `VAR=value` line to `~/.babelscore/.env`; creates file + parent dirs if absent

---

## config.json additions

Add to `"llms"`:

| Key | Provider |
|---|---|
| `openrouter` | OpenRouter (`https://openrouter.ai/api/v1`) |
| `groq` | Groq (`https://api.groq.com/openai/v1`) |
| `together` | Together AI (`https://api.together.xyz/v1`) |
| `litellm` | LiteLLM proxy (`http://localhost:4000/v1`) |
| `portkey` | Portkey (`https://api.portkey.ai/v1`) |
| `azure` | Azure OpenAI (placeholder URL, user must edit) |

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `config.json` missing/corrupt | Fall through to Custom-only mode, warn once |
| Provider selected, URL edited to blank | Re-prompt URL |
| Key found in env but empty string | Treat as not found — prompt |
| Key prompt left blank | Re-prompt (only for `key_reqd: true` providers) |
| `~/.babelscore/.env` not writable | Print warning, continue without saving |
| Ctrl+C during provider select | Existing wizard cancellation — no files written |
