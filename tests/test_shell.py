import pytest
from unittest.mock import patch, MagicMock
from babelscore.cli.shell import dispatch, COMMANDS


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


def test_dispatch_exit_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        dispatch("/exit")


def test_dispatch_quit_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        dispatch("/quit")


def test_all_commands_registered():
    for cmd in ["/init", "/help", "/exit", "/quit"]:
        assert cmd in COMMANDS
