import pytest
from unittest.mock import patch, MagicMock
from babelscore.cli.init_wizard import fetch_models, slug_from_url


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
