# BabelScore TUI — Functionality

## Overview

BabelScore's interactive shell is a Rich-rendered REPL launched by running `babelscore` with no subcommand. It is not a full-screen TUI — it renders styled output inline in the terminal, modelled on Claude Code's interaction style.

## Launch Behaviour

On startup the shell:
1. Clears nothing — output appends below whatever is in the terminal
2. Renders a large block-style ASCII art banner with the BabelScore name (cyan)
3. Prints the tagline and version/hint line beneath the banner
4. Drops to an interactive prompt: `> `

The ASCII logo is defined as `ASCII_LOGO` in `babelscore/cli/shell.py` and can be replaced freely.

## Prompt

The prompt is powered by `prompt_toolkit`, which provides:
- Command history navigation with ↑ / ↓ arrow keys
- Slash command autocomplete dropdown — type `/` to see all available commands; filters as you type
- A styled cyan `> ` prompt indicator

## Input Handling

| Input | Behaviour |
|---|---|
| `/command` | Dispatched to the matching slash command handler |
| Unknown `/command` | Prints an error: `Unknown command. Type /help for available commands.` |
| Non-slash input | Prints hint: `Commands start with /. Type /help for options.` |
| Empty input (Enter) | No-op, re-shows prompt |
| `Ctrl+C` | Prints `Goodbye.` and exits cleanly |
| `Escape` | Same as Ctrl+C |
| `/quit` | Same as Ctrl+C |

## Output Style

All output uses Rich for formatting:
- Panels for command responses (cyan border for `/init`, dim for `/help`)
- No raw `print()` calls in shell code

## Lifecycle

```
babelscore (no args)
    └── print_banner()
    └── REPL loop
            ├── prompt_toolkit prompt (with autocomplete)
            ├── parse input
            ├── dispatch to handler
            └── repeat until exit
```
