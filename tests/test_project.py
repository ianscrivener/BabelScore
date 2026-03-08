import json
import yaml
from unittest.mock import patch
from babelscore.config.project import create_project, project_exists


SAMPLE_CONFIG = {
    "project": "test-proj",
    "paradigm": 2,
    "source_language": "English",
    "target_language": "French",
    "translator_models": [
        {"name": "gpt-4o-mini", "base_url": "https://api.openai.com/v1", "api_key": "${OPENAI_API_KEY}"}
    ],
    "judge_models": [
        {"name": "claude-sonnet-4-6", "base_url": "https://api.anthropic.com/v1", "api_key": "${ANTHROPIC_API_KEY}"}
    ],
    "output": {
        "format": "markdown",
        "show_judge_reasoning": True,
        "flag_high_variance": True,
    },
}


def test_create_project_creates_dirs(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        create_project(SAMPLE_CONFIG)
    proj_dir = tmp_path / "test-proj"
    assert (proj_dir / "data").is_dir()
    assert (proj_dir / "results").is_dir()


def test_create_project_writes_config_yaml(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        create_project(SAMPLE_CONFIG)
    config_path = tmp_path / "test-proj" / "config.yaml"
    assert config_path.exists()
    loaded = yaml.safe_load(config_path.read_text())
    assert loaded["project"] == "test-proj"
    assert loaded["source_language"] == "English"


def test_project_exists_true(tmp_path):
    (tmp_path / "existing-proj").mkdir()
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        assert project_exists("existing-proj") is True


def test_project_exists_false(tmp_path):
    with patch("babelscore.config.project.PROJECTS_DIR", tmp_path):
        assert project_exists("no-such-proj") is False


def test_save_model_cache_writes_json(tmp_path):
    with patch("babelscore.config.project.BABELSCORE_DIR", tmp_path):
        from babelscore.config.project import save_model_cache
        save_model_cache("api.openai.com", ["gpt-4o", "gpt-4o-mini"])
    cache_path = tmp_path / "providers" / "api.openai.com" / "models.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text())
    assert "gpt-4o" in data
