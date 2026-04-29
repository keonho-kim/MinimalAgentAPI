import os
import tomllib
from pathlib import Path


def set_config(file_name: str = "env.toml") -> None:
    config_file = _find_config_file(file_name)

    with config_file.open("rb") as f:
        data = tomllib.load(f)

        # LOAD FS CONFIG
        _fs_config = data.get("fs")
        os.environ["AGENT_RUNTIME_ROOT_DIR"] = str(_fs_config.get("workspace"))

        # LOAD LLM CONFIG
        _llm_config = data.get("llm")

        os.environ["LLM_BASE_URL"] = str(_llm_config.get("base_url"))
        os.environ["LLM_MODEL_NAME"] = str(_llm_config.get("model_name"))
        os.environ["LLM_MAX_TOKENS"] = str(_llm_config.get("max_tokens"))
        os.environ["LLM_API_KEY"] = str(_llm_config.get("api_key"))


def _find_config_file(file_name: str) -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]

    for base_dir in candidates:
        config_file = base_dir / file_name
        if config_file.is_file():
            return config_file

    searched = ", ".join(str(base_dir / file_name) for base_dir in candidates)
    raise FileNotFoundError(f"Could not find {file_name}. Searched: {searched}")
