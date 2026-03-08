# BabelScore TUI — Slash Commands

## Command Reference

| Command | Status | Description |
|---|---|---|
| `/init` | Milestone 1 — stub | Start a new BabelScore evaluation project |
| `/help` | Milestone 1 | List available commands |
| `/exit` | Milestone 1 | Exit the shell |
| `/quit` | Milestone 1 | Alias for `/exit` |
| `/run` | Future | Run an evaluation for a named project |
| `/results` | Future | Display results for a named project |
| `/list` | Future | List all configured projects |
| `/config` | Future | Show or edit a project's config |

## Milestone 1 Behaviour

### `/init`

Displays a Rich panel explaining what the command will do when implemented. Takes no action, writes no files.

```
╭─ /init ──────────────────────────────────────────────────╮
│  BabelScore project initialisation                       │
│                                                          │
│  This command will guide you through creating a new      │
│  evaluation project — language pair, translator models,  │
│  judge models, and test data.                            │
│                                                          │
│  Coming soon.                                            │
╰──────────────────────────────────────────────────────────╯
```

### `/help`

Lists all available slash commands with a one-line description each.

### `/exit` / `/quit`

Prints `Goodbye.` and exits the process cleanly.

## Command Dispatch Architecture

Commands are registered in a dict in `shell.py`:

```python
COMMANDS = {
    "/init":  cmd_init,
    "/help":  cmd_help,
    "/exit":  cmd_exit,
    "/quit":  cmd_exit,
}
```

Each handler is a plain function that receives no arguments for Milestone 1. Future commands will receive parsed arguments.
