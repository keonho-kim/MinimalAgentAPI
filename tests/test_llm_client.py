import os
import json

import pytest

from minial_agent.common.config.loader import set_config
from minial_agent.common.llm import client as llm_module


LLM_ENV_KEYS = [
    "MINIAL_AGENT_MOUNT_UI",
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_MODEL_NAME",
    "LLM_MAX_TOKENS",
    "LLM_API_KEY",
    "LLM_KWARGS",
    "LLM_TLS_VERIFY",
    "LLM_CA_BUNDLE_PATH",
]


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    for key in LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_llm_env(
    monkeypatch,
    *,
    provider: str,
    base_url: str | None = None,
    max_tokens: str = "128",
    kwargs: dict | None = None,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MAX_TOKENS", max_tokens)
    monkeypatch.setenv("LLM_KWARGS", json.dumps(kwargs or {}))
    monkeypatch.setenv("LLM_TLS_VERIFY", "true")
    if base_url is not None:
        monkeypatch.setenv("LLM_BASE_URL", base_url)


def test_llm_client_uses_openai_compatible_provider(monkeypatch) -> None:
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return {"provider": "openai-compatible"}

    monkeypatch.setattr(llm_module, "ChatOpenAI", fake_chat_openai)
    _set_llm_env(
        monkeypatch,
        provider="openai-compatible",
        base_url="http://localhost:8000/v1",
        kwargs={"extra_body": {"enable_thinking": True}},
    )

    result = llm_module.llm_client(disable_streaming=True)

    assert result == {"provider": "openai-compatible"}
    assert captured["model"] == "test-model"
    assert captured["base_url"] == "http://localhost:8000/v1"
    assert captured["api_key"].get_secret_value() == "test-key"
    assert captured["max_tokens"] == 128
    assert captured["stream_usage"] is True
    assert captured["disable_streaming"] is True
    assert captured["extra_body"] == {"enable_thinking": True}


def test_llm_client_uses_openai_provider_without_compatible_options(
    monkeypatch,
) -> None:
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return {"provider": "openai"}

    monkeypatch.setattr(llm_module, "ChatOpenAI", fake_chat_openai)
    _set_llm_env(monkeypatch, provider="openai")

    result = llm_module.llm_client()

    assert result == {"provider": "openai"}
    assert captured["model"] == "test-model"
    assert captured["api_key"].get_secret_value() == "test-key"
    assert captured["max_tokens"] == 128
    assert "base_url" not in captured
    assert "extra_body" not in captured


def test_llm_client_uses_google_provider(monkeypatch) -> None:
    captured = {}

    def fake_google(**kwargs):
        captured.update(kwargs)
        return {"provider": "google"}

    monkeypatch.setattr(llm_module, "ChatGoogleGenerativeAI", fake_google)
    _set_llm_env(monkeypatch, provider="google", kwargs={"temperature": 0.2})

    result = llm_module.llm_client(disable_streaming=True)

    assert result == {"provider": "google"}
    assert captured["model"] == "test-model"
    assert captured["api_key"].get_secret_value() == "test-key"
    assert captured["max_tokens"] == 128
    assert captured["disable_streaming"] is True
    assert captured["temperature"] == 0.2


def test_llm_client_uses_anthropic_provider(monkeypatch) -> None:
    captured = {}

    def fake_anthropic(**kwargs):
        captured.update(kwargs)
        return {"provider": "anthropic"}

    monkeypatch.setattr(llm_module, "ChatAnthropic", fake_anthropic)
    _set_llm_env(monkeypatch, provider="anthropic", kwargs={"temperature": 0.2})

    result = llm_module.llm_client()

    assert result == {"provider": "anthropic"}
    assert captured["model_name"] == "test-model"
    assert captured["api_key"].get_secret_value() == "test-key"
    assert captured["max_tokens"] == 128
    assert captured["temperature"] == 0.2


def test_llm_client_rejects_unknown_provider(monkeypatch) -> None:
    _set_llm_env(monkeypatch, provider="ollama")

    with pytest.raises(ValueError, match="Unsupported LLM provider: ollama"):
        llm_module.llm_client()


def test_llm_client_requires_model_and_api_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    with pytest.raises(ValueError, match="LLM_MODEL_NAME"):
        llm_module.llm_client()

    monkeypatch.setenv("LLM_MODEL_NAME", "test-model")
    monkeypatch.delenv("LLM_API_KEY")

    with pytest.raises(ValueError, match="LLM_API_KEY"):
        llm_module.llm_client()


def test_llm_client_requires_base_url_for_openai_compatible(monkeypatch) -> None:
    _set_llm_env(monkeypatch, provider="openai-compatible")

    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        llm_module.llm_client()


def test_llm_client_rejects_invalid_kwargs_json(monkeypatch) -> None:
    _set_llm_env(monkeypatch, provider="openai")
    monkeypatch.setenv("LLM_KWARGS", "[]")

    with pytest.raises(ValueError, match="LLM_KWARGS must be a JSON object"):
        llm_module.llm_client()


def test_config_loader_sets_llm_provider(tmp_path, monkeypatch) -> None:
    config_file = tmp_path / "env.backend.toml"
    config_file.write_text(
        """
[serving]
mount_ui=false

[fs]
workspace="./tmpWorkspace/"

[llm]
provider="google"
model_name="gemini-2.5-flash"
api_key="test-key"
max_tokens=256
tls_verify=true

[llm.kwargs]
temperature=0.2
top_p=0.9
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    set_config("env.backend.toml")

    assert os.environ["MINIAL_AGENT_MOUNT_UI"] == "false"
    assert os.environ["LLM_PROVIDER"] == "google"
    assert os.environ["LLM_BASE_URL"] == ""
    assert os.environ["LLM_MODEL_NAME"] == "gemini-2.5-flash"
    assert os.environ["LLM_API_KEY"] == "test-key"
    assert os.environ["LLM_MAX_TOKENS"] == "256"
    assert json.loads(os.environ["LLM_KWARGS"]) == {
        "temperature": 0.2,
        "top_p": 0.9,
    }
