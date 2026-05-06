import json
import os

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def llm_client(*, disable_streaming: bool | str = False) -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "openai-compatible").strip()
    model = _required_env("LLM_MODEL_NAME")
    api_key = SecretStr(_required_env("LLM_API_KEY"))
    max_tokens = _max_tokens()
    llm_kwargs = _llm_kwargs()

    if provider == "openai-compatible":
        return ChatOpenAI(
            model=model,
            base_url=_required_env("LLM_BASE_URL"),
            api_key=api_key,
            max_tokens=max_tokens,
            stream_usage=True,
            disable_streaming=disable_streaming,
            **_http_client_config(),
            **llm_kwargs,
        )

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            stream_usage=True,
            disable_streaming=disable_streaming,
            **_http_client_config(),
            **llm_kwargs,
        )

    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            disable_streaming=disable_streaming,
            **llm_kwargs,
        )

    if provider == "anthropic":
        return ChatAnthropic(
            model_name=model,
            api_key=api_key,
            max_tokens=max_tokens,
            disable_streaming=disable_streaming,
            **llm_kwargs,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _max_tokens() -> int | None:
    value = os.getenv("LLM_MAX_TOKENS", "").strip()
    return int(value) if value else None


def _llm_kwargs() -> dict:
    value = os.getenv("LLM_KWARGS", "").strip()
    if not value:
        return {}

    try:
        kwargs = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid LLM_KWARGS JSON") from exc

    if not isinstance(kwargs, dict):
        raise ValueError("LLM_KWARGS must be a JSON object")
    return kwargs


def _http_client_config() -> dict:
    http_verify = _http_verify()
    if http_verify is True:
        return {}
    return {
        "http_client": httpx.Client(verify=http_verify),
        "http_async_client": httpx.AsyncClient(verify=http_verify),
    }


def _http_verify() -> bool | str:
    tls_verify = os.getenv("LLM_TLS_VERIFY", "true").lower()
    if tls_verify in {"0", "false", "no", "off"}:
        return False

    ca_bundle_path = os.getenv("LLM_CA_BUNDLE_PATH")
    if ca_bundle_path:
        return ca_bundle_path

    return True
