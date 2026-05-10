from pathlib import Path
from typing import Any

from minial_agent.integrations.pptx.ingest import ingest_pptx_deck


def build_pptx_preview(source_path: Path) -> dict[str, Any]:
    return ingest_pptx_deck(source_path).model_dump(mode="json")
