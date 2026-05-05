import os

import httpx
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def llm_client(*, disable_streaming: bool | str = False) -> ChatOpenAI:
    max_tokens = os.getenv("LLM_MAX_TOKENS")
    http_verify = _http_verify()
    http_client_config = (
        {}
        if http_verify is True
        else {
            "http_client": httpx.Client(verify=http_verify),
            "http_async_client": httpx.AsyncClient(verify=http_verify),
        }
    )

    return ChatOpenAI(
        model=os.getenv("LLM_MODEL_NAME", ""),
        base_url=os.getenv("LLM_BASE_URL", ""),
        api_key=SecretStr(os.getenv("LLM_API_KEY", "")),
        max_tokens=int(max_tokens) if max_tokens else None,
        stream_usage=True,
        disable_streaming=disable_streaming,
        extra_body={"enable_thinking": True},
        **http_client_config,
    )


def _http_verify() -> bool | str:
    tls_verify = os.getenv("LLM_TLS_VERIFY", "true").lower()
    if tls_verify in {"0", "false", "no", "off"}:
        return False

    ca_bundle_path = os.getenv("LLM_CA_BUNDLE_PATH")
    if ca_bundle_path:
        return ca_bundle_path

    return True
