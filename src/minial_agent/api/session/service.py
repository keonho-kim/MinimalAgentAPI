from textwrap import dedent
from typing import Any

from minial_agent.common.llm import llm_client

MAX_TITLE_CHARS = 10
DEFAULT_TITLE = "New session"
TITLE_SYSTEM_PROMPT = dedent(
    """
    Create a concise Korean chat title from the provided chat exchange.
    Return only the title in KOREAN. Do not include quotes, punctuation, or explanation.
    Keep it within 10 characters.
    """.strip()
)


class SessionService:
    def create_title(self, *, user_id: str, uuid: str, message: str) -> str:
        _ = (user_id, uuid)
        response = llm_client(disable_streaming=True).invoke(
            [
                ("system", TITLE_SYSTEM_PROMPT),
                ("user", message.strip()),
            ]
        )
        return clean_session_title(_message_content_text(response), fallback=message)


def clean_session_title(raw_title: str, *, fallback: str = DEFAULT_TITLE) -> str:
    title = _first_line(raw_title) or _first_line(fallback) or DEFAULT_TITLE
    title = title.strip().strip("\"'`“”‘’")
    title = _strip_title_prefix(title)
    title = title.strip().strip("\"'`“”‘’")
    title = " ".join(title.split())
    title = title.rstrip(".。!！?？,，")
    if not title:
        title = DEFAULT_TITLE
    return "".join(list(title)[:MAX_TITLE_CHARS])


def _message_content_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts)
    return str(content)


def _first_line(value: str) -> str:
    for line in value.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def _strip_title_prefix(title: str) -> str:
    lowered = title.lower()
    for prefix in ("title:", "title：", "제목:", "제목："):
        if lowered.startswith(prefix):
            return title[len(prefix) :].strip()
    return title


session_service = SessionService()
