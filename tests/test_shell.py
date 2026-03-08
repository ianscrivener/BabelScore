import pytest
from unittest.mock import patch, MagicMock
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from babelscore.cli.shell import dispatch, run_shell, COMMANDS


def test_dispatch_unknown_command_prints_error():
    with patch("babelscore.cli.shell.console") as mock_console:
        dispatch("/foobar")
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "Unknown command" in args


def test_dispatch_non_slash_input_prints_hint():
    with patch("babelscore.cli.shell.console") as mock_console:
        dispatch("hello")
        mock_console.print.assert_called_once()
        args = mock_console.print.call_args[0][0]
        assert "/" in args


def test_dispatch_init_calls_cmd_init():
    mock_fn = MagicMock()
    with patch.dict(COMMANDS, {"/init": mock_fn}):
        dispatch("/init")
        mock_fn.assert_called_once()


def test_dispatch_quit_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        dispatch("/quit")


def test_all_commands_registered():
    for cmd in ["/init", "/help", "/quit"]:
        assert cmd in COMMANDS


# ── run_shell integration tests (prompt_toolkit pipe input) ───────────────────


def test_run_shell_quit_exits_cleanly():
    with create_pipe_input() as inp:
        inp.send_text("/quit\n")
        with patch("babelscore.cli.shell.console") as mock_console:
            run_shell(_input=inp, _output=DummyOutput())
    mock_console.print.assert_called_with("\n[dim]Goodbye.[/dim]")


def test_run_shell_eof_exits_cleanly():
    """Ctrl+D (EOFError) should print Goodbye and exit."""
    with create_pipe_input() as inp:
        inp.send_text("\x04")  # EOT — prompt_toolkit raises EOFError
        with patch("babelscore.cli.shell.console") as mock_console:
            run_shell(_input=inp, _output=DummyOutput())
    mock_console.print.assert_called_with("\n[dim]Goodbye.[/dim]")


def test_run_shell_unknown_command_shows_error():
    with create_pipe_input() as inp:
        inp.send_text("/foobar\n")
        inp.send_text("/quit\n")
        with patch("babelscore.cli.shell.console") as mock_console:
            run_shell(_input=inp, _output=DummyOutput())
    all_printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "Unknown command" in all_printed


def test_run_shell_non_slash_input_shows_hint():
    with create_pipe_input() as inp:
        inp.send_text("hello\n")
        inp.send_text("/quit\n")
        with patch("babelscore.cli.shell.console") as mock_console:
            run_shell(_input=inp, _output=DummyOutput())
    all_printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "/" in all_printed


def test_run_shell_empty_input_continues():
    """Empty lines are silently ignored — loop continues."""
    with create_pipe_input() as inp:
        inp.send_text("\n")
        inp.send_text("/quit\n")
        with patch("babelscore.cli.shell.console"):
            run_shell(_input=inp, _output=DummyOutput())


def test_run_shell_help_runs_without_error():
    with create_pipe_input() as inp:
        inp.send_text("/help\n")
        inp.send_text("/quit\n")
        with patch("babelscore.cli.shell.console"):
            run_shell(_input=inp, _output=DummyOutput())
