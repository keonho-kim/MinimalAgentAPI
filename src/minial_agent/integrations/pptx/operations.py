from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation

from minial_agent.integrations.pptx.ingest import load_or_ingest_pptx_deck
from minial_agent.integrations.pptx.model import (
    PptxOperation,
    PptxOperationResponse,
)
from minial_agent.integrations.pptx.operation_guards import manual_override_violation
from minial_agent.integrations.pptx.operation_mutations import apply_operation
from minial_agent.integrations.pptx.store import PptxDeckStore, pptx_db_path


def apply_pptx_operations(
    *,
    cache_dir: Path,
    source_path: Path,
    expected_revision: int,
    origin: str,
    operations: list[PptxOperation],
) -> PptxOperationResponse:
    deck = load_or_ingest_pptx_deck(cache_dir=cache_dir, source_path=source_path)
    if deck.revision != expected_revision:
        raise ValueError(
            f"PPTX deck revision mismatch: expected {expected_revision}, current {deck.revision}"
        )

    editable_deck = deck.model_copy(deep=True)
    presentation = Presentation(source_path)
    changed_slide_ids: list[str] = []
    rejected: list[dict[str, Any]] = []

    for operation in operations:
        violation = manual_override_violation(editable_deck, operation, origin=origin)
        if violation:
            rejected.append(
                {"operation": operation.model_dump(mode="json"), "reason": violation}
            )
            continue
        changed_slide_id = apply_operation(
            presentation=presentation,
            deck=editable_deck,
            operation=operation,
            origin=origin,
        )
        if changed_slide_id and changed_slide_id not in changed_slide_ids:
            changed_slide_ids.append(changed_slide_id)

    if rejected and not changed_slide_ids:
        return PptxOperationResponse(
            path=str(source_path),
            revision=editable_deck.revision,
            changed_slide_ids=[],
            rejected_operations=rejected,
            deck=editable_deck,
        )

    if changed_slide_ids:
        editable_deck.revision += 1
        presentation.save(source_path)
        store = PptxDeckStore(pptx_db_path(cache_dir, source_path))
        store.save(editable_deck, source_stat=_source_stat(source_path))
        store.record_edit(
            deck_id=editable_deck.id,
            revision=editable_deck.revision,
            origin=origin,
            operations=[operation.model_dump(mode="json") for operation in operations],
            changed_slide_ids=changed_slide_ids,
        )

    return PptxOperationResponse(
        path=str(source_path),
        revision=editable_deck.revision,
        changed_slide_ids=changed_slide_ids,
        rejected_operations=rejected,
        deck=editable_deck,
    )


def _source_stat(source_path: Path) -> dict[str, int | str]:
    stat = source_path.stat()
    return {
        "path": str(source_path.resolve()),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }
