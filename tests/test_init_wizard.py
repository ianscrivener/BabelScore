import yaml
from unittest.mock import patch, MagicMock
from babelscore.cli.init_wizard import (
    fetch_models,
    slug_from_url,
    normalise_url,
    run_wizard,
)


def test_slug_from_url_strips_protocol():
    assert slug_from_url("https://api.openai.com/v1") == "api.openai.com"


def test_slug_from_url_localhost():
    assert slug_from_url("http://localhost:11434/v1") == "localhost"


def test_fetch_models_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]
    }
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models == ["gpt-4o", "gpt-4o-mini"]


def test_fetch_models_http_error_returns_none():
    with patch("babelscore.cli.init_wizard.httpx.get", side_effect=Exception("timeout")):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None


def test_fetch_models_bad_status_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 401
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None


def test_fetch_models_empty_data_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    with patch("babelscore.cli.init_wizard.httpx.get", return_value=mock_response):
        models = fetch_models("https://api.openai.com/v1", "sk-test")
    assert models is None


def test_run_wizard_cancelled_writes_nothing(tmp_path):
    """Ctrl+C during wizard must not create any files."""
    with patch("babelscore.cli.init_wizard.prompt", side_effect=KeyboardInterrupt), \
         patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        from babelscore.cli.init_wizard import run_wizard
        run_wizard()
    assert list(tmp_path.iterdir()) == []


def test_run_wizard_existing_project_warns(tmp_path):
    """If project already exists, wizard warns before proceeding."""
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path), \
         patch("babelscore.cli.init_wizard.project_exists", return_value=True), \
         patch("babelscore.cli.init_wizard.prompt", side_effect=["my-project", KeyboardInterrupt]), \
         patch("babelscore.cli.init_wizard.console") as mock_console:
        run_wizard()
    printed = " ".join(str(c) for c in mock_console.print.call_args_list)
    assert "already exists" in printed.lower() or "exist" in printed.lower()


# ── normalise_url ──────────────────────────────────────────────────────────────

def test_normalise_url_adds_https():
    assert normalise_url("api.openai.com/v1") == "https://api.openai.com/v1"


def test_normalise_url_leaves_https_intact():
    assert normalise_url("https://api.openai.com/v1") == "https://api.openai.com/v1"


def test_normalise_url_leaves_http_intact():
    assert normalise_url("http://localhost:11434/v1") == "http://localhost:11434/v1"


def test_normalise_url_empty_string():
    assert normalise_url("") == ""


# ── run_wizard integration ─────────────────────────────────────────────────────

# Prompt order (with fetch_models returning None → manual model entry):
#  0  project name
#  1  source lang
#  2  target lang
#  3  translator base URL
#  4  translator API key
#  5  translator model name (manual fallback)
#  6  judge base URL
#  7  judge API key
#  8  judge model name (manual fallback)
#  9  show reasoning [Y/n]
# 10  flag variance  [Y/n]

_HAPPY_INPUTS = [
    "en-fr-test",
    "English",
    "French",
    "https://api.openai.com/v1",
    "OPENAI_API_KEY",
    "gpt-4o-mini",
    "https://api.anthropic.com/v1",
    "ANTHROPIC_API_KEY",
    "claude-sonnet-4-6",
    "y",
    "n",
]


def _run_wizard_with(inputs, tmp_path, *, fetch_return=None, extra_patches=None):
    """Run wizard with canned prompt responses; patches PROJECTS_DIR to tmp_path."""
    patches = [
        patch("babelscore.cli.init_wizard.prompt", side_effect=list(inputs)),
        patch("babelscore.cli.init_wizard.fetch_models", return_value=fetch_return),
        patch("babelscore.cli.init_wizard.console"),
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


def test_run_wizard_happy_path_creates_config(tmp_path):
    _run_wizard_with(_HAPPY_INPUTS, tmp_path)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["project"] == "en-fr-test"
    assert config["source_language"] == "English"
    assert config["target_language"] == "French"
    assert config["paradigm"] == 2
    assert config["translator_models"][0]["name"] == "gpt-4o-mini"
    assert config["judge_models"][0]["name"] == "claude-sonnet-4-6"
    assert config["output"]["show_judge_reasoning"] is True
    assert config["output"]["flag_high_variance"] is False


def test_run_wizard_creates_data_and_results_dirs(tmp_path):
    _run_wizard_with(_HAPPY_INPUTS, tmp_path)
    proj = tmp_path / "en-fr-test"
    assert (proj / "data").is_dir()
    assert (proj / "results").is_dir()


def test_run_wizard_empty_name_aborts(tmp_path):
    _run_wizard_with([""], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_run_wizard_existing_project_overwrite_yes(tmp_path):
    (tmp_path / "en-fr-test").mkdir()
    inputs = ["en-fr-test", "y"] + _HAPPY_INPUTS[1:]
    _run_wizard_with(inputs, tmp_path)
    assert (tmp_path / "en-fr-test" / "config.yaml").exists()


def test_run_wizard_existing_project_overwrite_no(tmp_path):
    (tmp_path / "en-fr-test").mkdir()
    _run_wizard_with(["en-fr-test", "n"], tmp_path)
    assert not (tmp_path / "en-fr-test" / "config.yaml").exists()


def test_run_wizard_bare_api_key_wrapped_as_env_ref(tmp_path):
    _run_wizard_with(_HAPPY_INPUTS, tmp_path)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["api_key"] == "${OPENAI_API_KEY}"
    assert config["judge_models"][0]["api_key"] == "${ANTHROPIC_API_KEY}"


def test_run_wizard_already_wrapped_key_unchanged(tmp_path):
    inputs = list(_HAPPY_INPUTS)
    inputs[4] = "${OPENAI_API_KEY}"   # translator key already wrapped
    inputs[7] = "${ANTHROPIC_API_KEY}"
    _run_wizard_with(inputs, tmp_path)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["api_key"] == "${OPENAI_API_KEY}"


def test_run_wizard_model_pick_by_number(tmp_path):
    # fetch_models returns a list; user picks "1" → first model selected
    inputs = list(_HAPPY_INPUTS)
    inputs[5] = "1"   # pick model by number
    inputs[8] = "1"
    _run_wizard_with(inputs, tmp_path, fetch_return=["gpt-4o", "gpt-4o-mini"])
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["name"] == "gpt-4o"
    assert config["judge_models"][0]["name"] == "gpt-4o"


def test_run_wizard_model_pick_by_name(tmp_path):
    # fetch_models returns a list; user types the name directly
    inputs = list(_HAPPY_INPUTS)
    inputs[5] = "gpt-4o-mini"
    inputs[8] = "gpt-4o-mini"
    _run_wizard_with(inputs, tmp_path, fetch_return=["gpt-4o", "gpt-4o-mini"])
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["name"] == "gpt-4o-mini"


def test_run_wizard_model_fetch_failure_uses_manual_entry(tmp_path):
    # fetch_models returns None → user types model name manually
    _run_wizard_with(_HAPPY_INPUTS, tmp_path, fetch_return=None)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["name"] == "gpt-4o-mini"


def test_run_wizard_url_without_protocol_normalised_in_config(tmp_path):
    """URL entered without https:// must be normalised before saving to config.yaml."""
    inputs = list(_HAPPY_INPUTS)
    inputs[3] = "api.openai.com/v1"        # no protocol — translator
    inputs[6] = "api.anthropic.com/v1"     # no protocol — judge
    _run_wizard_with(inputs, tmp_path)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["translator_models"][0]["base_url"] == "https://api.openai.com/v1"
    assert config["judge_models"][0]["base_url"] == "https://api.anthropic.com/v1"


def test_run_wizard_output_yes_defaults(tmp_path):
    """[Y/n] prompts: 'y' → True, '' (empty Enter) is also treated as True (not 'n')."""
    inputs = list(_HAPPY_INPUTS)
    inputs[9] = ""   # empty Enter → not "n" → show_judge_reasoning = True
    inputs[10] = ""  # empty Enter → not "n" → flag_high_variance = True
    _run_wizard_with(inputs, tmp_path)
    config = yaml.safe_load((tmp_path / "en-fr-test" / "config.yaml").read_text())
    assert config["output"]["show_judge_reasoning"] is True
    assert config["output"]["flag_high_variance"] is True
