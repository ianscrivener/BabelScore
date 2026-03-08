# BabelScore — Tech Stack & Dev Sequence

*Last updated: March 8, 2026*

---

## Tech Stack

### Language & Tooling

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Stable, broad ecosystem, excellent asyncio. Too early for 3.13. |
| Package manager | UV | 10-100x faster than pip, handles venv + lockfile in one tool, modern standard for new projects |
| Dependency file | `pyproject.toml` | UV-native, replaces setup.py + requirements.txt |
| Linter/formatter | Ruff | Fast, UV-native, replaces black + flake8 |

### Core Libraries

| Component | Library | Role |
|---|---|---|
| TUI / CLI wizard | Textual | Interactive terminal UI — wizard, live progress, results display |
| Terminal output | Rich | Tables, markdown rendering, log formatting (Textual dependency) |
| CLI entrypoint | Click | Command routing — `babelscore init`, `babelscore run`, etc. |
| HTTP client | httpx | Async HTTP — all API calls to translator and judge models |
| Async orchestration | asyncio | Parallel translation and judge calls |
| Config | PyYAML | Read/write project config.yaml |
| Env vars | python-dotenv | Load `~/.babelscore/.env` |
| Data | csv (stdlib) | Test set input — no pandas dependency for simplicity |
| Output | Rich / Jinja2 | Scorecard rendering to terminal and markdown file |

### UI (Phase 2)

| Component | Library | Role |
|---|---|---|
| Browser UI | Streamlit | HuggingFace Spaces deployment |

### Dev & CI

| Component | Tool |
|---|---|
| Testing | pytest + pytest-asyncio |
| Type checking | mypy |
| CI | GitHub Actions |

---

## Repository Structure

```
babelscore/
├── pyproject.toml
├── README.md
├── .env.example
│
├── babelscore/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py       # main evaluation pipeline
│   │   ├── translator.py     # async translation calls
│   │   ├── judge.py          # async judge calls
│   │   ├── scorer.py         # aggregation + variance
│   │   └── models.py         # pydantic config models
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py           # click entrypoint
│   │   ├── wizard.py         # Textual wizard app
│   │   └── results.py        # Rich scorecard renderer
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py         # config validation
│   │   └── project.py        # project read/write/list
│   │
│   └── ui/                   # Phase 2
│       └── app.py            # Streamlit app
│
├── tests/
│   ├── test_pipeline.py
│   ├── test_translator.py
│   └── test_judge.py
│
└── docs/
    ├── BabelScore_Brainstorm_Summary.md
    └── BabelScore_Tech_Stack_Dev_Sequence.md
```

---

## Dev Sequence

### Phase 1 — Happy Path End-to-End

Goal: one translator model, one judge model, Paradigm 2 (one-way, cold judge), 5 sentences, scorecard prints to terminal. Nothing more.

| Step | Task | Notes |
|---|---|---|
| 1 | Repo scaffold | `uv init`, pyproject.toml, folder structure, Click entrypoint |
| 2 | Config schema | Pydantic model for config.yaml — translator, judge, language pair, paradigm |
| 3 | `translator.py` | Single async httpx call to OpenAI-compatible endpoint |
| 4 | `judge.py` | Single async httpx call, returns score + reasoning |
| 5 | `pipeline.py` | Sequential call to translator then judge for one sentence |
| 6 | `scorer.py` | Mean score, basic output dict |
| 7 | `results.py` | Rich table printed to terminal |
| 8 | `babelscore run` | Wire everything together, run from a hand-edited config.yaml |
| 9 | Manual test | 5 English→French sentences, one translator, one judge, confirm output |

**Exit criteria:** `babelscore run my-project` produces a scorecard from a hand-crafted config.yaml and CSV. No wizard yet.

---

### Phase 2 — Parallelism + Multiple Models

Goal: N translators × M judges running concurrently, with aggregated scorecard and variance flagging.

| Step | Task | Notes |
|---|---|---|
| 10 | Async batch translation | `asyncio.gather` across all sentences × all translator models |
| 11 | Async batch judging | `asyncio.gather` across all translations × all judge models |
| 12 | Rate limiting | Per-provider concurrency limits, exponential backoff on 429s |
| 13 | Scorer upgrade | Per-model mean, per-judge mean, variance flag, judge agreement |
| 14 | Results upgrade | Multi-model comparison table, flag high-variance rows |
| 15 | Manual test | 25 sentences, 3 translators, 2 judges, confirm scorecard |

---

### Phase 3 — All Five Paradigms

Goal: full paradigm coverage, reference translation support, bidirectional testing.

| Step | Task | Notes |
|---|---|---|
| 16 | Paradigm 1 | Round-trip back-translation, string similarity scoring |
| 17 | Paradigm 3 | One-way + reference, judge prompt includes reference |
| 18 | Paradigm 4 | Bidirectional, cold judge, two scorecards |
| 19 | Paradigm 5 | Bidirectional + reference — gold standard path |
| 20 | CSV validation | Detect which paradigm the data supports, warn if mismatch |

---

### Phase 4 — Textual Wizard

Goal: `babelscore init` launches a Textual TUI that walks through the two wizard questions and writes config.yaml.

| Step | Task | Notes |
|---|---|---|
| 21 | Wizard Q1 | What are you testing — 1a/1b/1c |
| 22 | Wizard Q2 | What data do you have — 2a/2b/2c |
| 23 | Paradigm derivation | Auto-select paradigm from Q1 + Q2 answers |
| 24 | Model configuration | Add translator models — name, base_url, api_key |
| 25 | Judge configuration | Add judge models — same fields |
| 26 | API key handling | Check env → check .env → prompt securely → save to .env |
| 27 | Write config.yaml | Confirm and save project |
| 28 | Live run progress | Textual progress panel during `babelscore run` |

---

### Phase 5 — Data Wizard & Synthetic Generation

Goal: support users with no test data — find or generate a parallel corpus.

| Step | Task | Notes |
|---|---|---|
| 29 | FLORES-200 fetch | Auto-download sentence pairs for supported language pairs |
| 30 | OPUS/Tatoeba | Point user to relevant corpus for their language pair |
| 31 | Synthetic generation | LLM generates parallel pairs from domain description |
| 32 | Review interface | Textual UI to accept/reject generated pairs before saving |

---

### Phase 6 — Streamlit + HuggingFace Spaces

Goal: browser UI for demos and community leaderboard.

| Step | Task | Notes |
|---|---|---|
| 33 | Streamlit app | Thin wrapper around core pipeline |
| 34 | Session key handling | Per-session only, never stored |
| 35 | HF Space deployment | Dockerfile + Space config |
| 36 | Community leaderboard | Read-only display of submitted BabelScores |

---

## BabelScore Version Pinning

Each published BabelScore version must document:

```yaml
babelscore_version: "1.0"
judges:
  - model: claude-sonnet-4-6
    base_url: https://api.anthropic.com/v1
  - model: gpt-4o-2024-08-06
    base_url: https://api.openai.com/v1
rubric_version: "1.0"
aggregation: mean
```

Results should always be reported as e.g. `BabelScore v1.0: 8.4 / 10`. Version bump required if any judge model, rubric, or aggregation method changes.

---

*Next step: Phase 1, Step 1 — repo scaffold.*
