import os

from minial_agent.common.config.loader import set_config


def test_set_config_loads_project_root_env() -> None:
    set_config("env.toml")

    assert os.environ["AGENT_RUNTIME_ROOT_DIR"] == "./tmpWorkspace/"
    assert os.environ["LLM_BASE_URL"] == "http://127.0.0.1:1234/v1"
    assert os.environ["LLM_MODEL_NAME"] == "google/gemma-4-e4b"
    assert os.environ["LLM_MAX_TOKENS"] == "8192"
    assert os.environ["LLM_API_KEY"] == "EMPTY"
