from datetime import datetime

from langchain_core.tools import tool


@tool
def get_today() -> str:
    """Return today's date in the server local timezone."""
    return datetime.now().astimezone().date().isoformat()


__all__ = ["get_today"]
