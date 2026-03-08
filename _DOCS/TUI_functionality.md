# BabelScore TUI — Functionality

## Overview

BabelScore's interactive shell is a Rich-rendered REPL launched by running `babelscore` with no subcommand. It is not a full-screen TUI — it renders styled output inline in the terminal, modelled on Claude Code's interaction style.

## Launch Behaviour

On startup the shell:
1. Clears nothing — output appends below whatever is in the terminal
2. Renders a large ASCII art banner with the BabelScore name
3. Prints a tagline and version/hint line beneath the banner
4. Drops to an interactive prompt: `> `

## Prompt

The prompt is powered by `prompt_toolkit`, which provides:
- Command history navigation with ↑ / ↓ arrow keys
- Tab-completion for slash commands
- A styled `> ` prompt indicator

## Input Handling

| Input | Behaviour |
|---|---|
| `/command` | Dispatched to the matching slash command handler |
| Unknown `/command` | Prints an error: `Unknown command. Type /help for available commands.` |
| Empty input (Enter) | No-op, re-shows prompt |
| `Ctrl+C` | Prints `Goodbye.` and exits cleanly |
| `Escape` | Same as Ctrl+C |
| `/exit` or `/quit` | Same as Ctrl+C |

## Output Style

All output uses Rich for formatting:
- Panels for command responses
- Consistent colour palette (to be defined)
- No raw `print()` calls in shell code

## Lifecycle

```
babelscore (no args)
    └── print_banner()
    └── REPL loop
            ├── prompt_toolkit prompt
            ├── parse input
            ├── dispatch to handler
            └── repeat until exit
```
