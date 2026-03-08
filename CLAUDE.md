# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
BabelScore is a CLI tool for benchmarking LLM translation quality using LLM-as-judge evaluation. It runs source sentences through N translator models, scores the output with M judge models, and produces an aggregated scorecard. Designed for low-resource languages where BLEU is unreliable.

## CLI Command
The CLI entrypoint is `babelscore`. Use this name everywhere — entrypoints, docs, help text.

## Virtual Environment
Always activate the UV virtual environment before running any Python or CLI commands:
```bash
source .venv/bin/activate
```
The alias `uvsrc` is available in the user's shell (`alias uvsrc="source .venv/bin/activate"`).

## Tooling
- Python 3.12 (pin in pyproject.toml)
- UV for package management (not pip) — always use `uv add <package>` to install, never edit pyproject.toml dependencies directly
- Ruff for linting and formatting
- Pydantic for config validation
- Click for CLI routing
- httpx for all async HTTP
- pytest + pytest-asyncio for testing
- Textual + Rich for TUI (Phase 4 — do not build yet)
- Streamlit (Phase 6 — do not build yet)

## API Constraint
All translator and judge models communicate via OpenAI-compatible chat completions endpoints only. No provider-specific SDKs. This covers OpenAI, Anthropic (via compatible wrappers), OpenRouter, Ollama, Together, Groq identically.

## Project Storage
Projects live at `~/.babelscore/projects/[project-name]/` with:
- `config.yaml` — canonical project state (never superseded by wizard or UI)
- `data/test_set.csv` — source sentences or parallel corpus
- `results/scorecard.md` — output

API keys are stored globally in `~/.babelscore/.env`. Key lookup order: environment variable → `~/.babelscore/.env` → prompted during init.

## Current Focus — Phase 1 Only
Build the simplest possible end-to-end happy path. Nothing outside these 9 steps:

1. Repo scaffold — `uv init`, pyproject.toml, folder structure, Click entrypoint
2. Config schema — Pydantic model for config.yaml
3. `translator.py` — single async httpx call to OpenAI-compatible endpoint
4. `judge.py` — single async httpx call, returns score + reasoning
5. `pipeline.py` — sequential translator then judge for one sentence
6. `scorer.py` — mean score, basic output dict
7. `results.py` — Rich table printed to terminal
8. `babelscore run` — wire everything together, run from config.yaml
9. Manual test — 5 English→French sentences, one translator, one judge

**Exit criteria:** `babelscore run my-project` produces a scorecard from a hand-crafted config.yaml and CSV file.

## Do Not Build Yet
- Textual wizard (`babelscore init`)
- Parallel/concurrent API calls
- Multiple translator or judge models
- Paradigms other than Paradigm 2 (one-way, cold judge)
- Streamlit UI
- Data generation or corpus fetching
- HuggingFace Spaces deployment

## Project Structure
```
babelscore/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── .env.example
├── babelscore/
│   ├── __init__.py
│   ├── core/
│   │   ├── pipeline.py       # main evaluation pipeline
│   │   ├── translator.py     # async translation calls
│   │   ├── judge.py          # async judge calls
│   │   ├── scorer.py         # aggregation + variance
│   │   └── models.py         # pydantic config models
│   ├── cli/
│   │   ├── main.py           # click entrypoint
│   │   └── results.py        # Rich scorecard renderer
│   └── config/
│       ├── schema.py         # config validation
│       └── project.py        # project read/write/list
└── tests/
    ├── test_pipeline.py
    ├── test_translator.py
    └── test_judge.py
```

## Config Format
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

## Test Data Format (Phase 1 — source sentences only)
```csv
source
"The committee has not yet reached a decision."
"She had already left before he arrived."
"If it rains tomorrow, we will stay home."
```

Parallel corpus format (Paradigms 3–5):
```csv
source_en,source_target
"The child is eating.","Pikinini i stap kakae."
```

## Evaluation Paradigms
| # | Description | Data Required |
|---|---|---|
| 1 | Round-trip back-translation, string similarity | Source sentences only |
| 2 | One-way, cold judge (no reference) | Source sentences only |
| 3 | One-way with reference | Source + reference translations |
| 4 | Bidirectional, cold judge | Parallel sentence pairs |
| 5 | Bidirectional with reference (gold standard) | Parallel sentence pairs |

## BabelScore Versioning
Results must cite version: `BabelScore v1.0: 8.4 / 10`. Version is defined by judge models + rubric + aggregation method. Version bump required if any of these change.

## Guardrails
Never modify, create, or delete files outside `/Users/ianscrivener/zzCODE26zz/BabelScore/` without explicit user approval in that message.

Never read `.env` under any circumstances whatsoever.

## Key Decisions (do not relitigate)
- OpenAI-compatible API format is mandatory — no exceptions
- UV not pip
- Python 3.12
- CLI command is `babelscore` not `babeltest`
- YAML is canonical project state regardless of how it was created
