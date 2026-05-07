import json
import os
import tomllib
from pathlib import Path


def set_config(file_name: str = "env.backend.toml") -> None:
    config_file = _find_config_file(file_name)

    with config_file.open("rb") as f:
        data = tomllib.load(f)

        # LOAD SERVING CONFIG
        _serving_config = data.get("serving", {})
        os.environ["MINIAL_AGENT_MOUNT_UI"] = str(
            _serving_config.get("mount_ui", True)
        ).lower()

        # LOAD FS CONFIG
        _fs_config = data.get("fs")
        os.environ["AGENT_RUNTIME_ROOT_DIR"] = str(_fs_config.get("workspace"))
        os.environ["AGENT_PAGE_SCAN_BATCH_SIZE"] = str(
            _positive_int(
                _fs_config.get("page_scan_batch_size", 10),
                name="fs.page_scan_batch_size",
            )
        )

        # LOAD LLM CONFIG
        _llm_config = data.get("llm", {})

        os.environ["LLM_PROVIDER"] = str(
            _llm_config.get("provider", "openai-compatible")
        )
        os.environ["LLM_BASE_URL"] = str(_llm_config.get("base_url", ""))
        os.environ["LLM_MODEL_NAME"] = str(_llm_config.get("model_name", ""))
        os.environ["LLM_MAX_TOKENS"] = str(_llm_config.get("max_tokens", ""))
        os.environ["LLM_API_KEY"] = str(_llm_config.get("api_key", ""))
        os.environ["LLM_KWARGS"] = json.dumps(_llm_config.get("kwargs", {}))
        os.environ["LLM_TLS_VERIFY"] = str(
            _llm_config.get("tls_verify", True)
        ).lower()
        ca_bundle_path = _llm_config.get("ca_bundle_path")
        if ca_bundle_path:
            os.environ["LLM_CA_BUNDLE_PATH"] = str(ca_bundle_path)
        else:
            os.environ.pop("LLM_CA_BUNDLE_PATH", None)

        # LOAD LLM SUMMARIZER CONFIG
        _llm_summary_config = data.get("llm", {}).get("summary", {})
        os.environ["LLM_SUMMARY_TRIGGER_TOKEN_SIZE"] = str(
            _llm_summary_config.get("trigger_token_size", 4096)
        )
        os.environ["LLM_SUMMARY_KEEP_MESSAGES"] = str(
            _llm_summary_config.get("keep_messages", 20)
        )


def _find_config_file(file_name: str) -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]

    for base_dir in candidates:
        config_file = base_dir / file_name
        if config_file.is_file():
            return config_file

    searched = ", ".join(str(base_dir / file_name) for base_dir in candidates)
    raise FileNotFoundError(f"Could not find {file_name}. Searched: {searched}")


def _positive_int(value: object, *, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer.") from exc
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return parsed
