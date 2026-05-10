from __future__ import annotations

from pathlib import Path

from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.fs.models import FsMutation
from minial_agent.integrations.fs.paths import resolve_file
from minial_agent.integrations.fs.workspace import get_workspace
from minial_agent.integrations.pptx.export import export_pptx_file, export_pptx_pdf
from minial_agent.integrations.pptx.ingest import load_or_ingest_pptx_deck
from minial_agent.integrations.pptx.operations import apply_pptx_operations
from minial_agent.integrations.pptx.model import (
    PptxDeck,
    PptxExportResponse,
    PptxOperation,
    PptxOperationResponse,
    PptxSearchResponse,
)
from minial_agent.integrations.pptx.store import PptxDeckStore, pptx_db_path
from minial_agent.integrations.upload.visibility import physical_to_public_workspace_path


def pptx_deck(*, user_id: str, uuid: str, path: str) -> tuple[FsMutation, PptxDeck]:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = _resolve_pptx(workspace.files_dir, path)
    deck = load_or_ingest_pptx_deck(cache_dir=workspace.cache_dir, source_path=target)
    return (
        FsMutation(path=physical_to_public_workspace_path(workspace.files_dir, target)),
        deck,
    )


def pptx_operations(
    *,
    user_id: str,
    uuid: str,
    path: str,
    origin: str,
    expected_revision: int,
    operations: list[PptxOperation],
) -> PptxOperationResponse:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = _resolve_pptx(workspace.files_dir, path)
    try:
        result = apply_pptx_operations(
            cache_dir=workspace.cache_dir,
            source_path=target,
            expected_revision=expected_revision,
            origin=origin,
            operations=operations,
        )
    except ValueError as exc:
        raise WorkspaceFsError(400, str(exc)) from exc
    return result.model_copy(
        update={"path": physical_to_public_workspace_path(workspace.files_dir, target)}
    )


def pptx_search(
    *,
    user_id: str,
    uuid: str,
    path: str,
    query: str,
    limit: int,
) -> PptxSearchResponse:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = _resolve_pptx(workspace.files_dir, path)
    load_or_ingest_pptx_deck(cache_dir=workspace.cache_dir, source_path=target)
    store = PptxDeckStore(pptx_db_path(workspace.cache_dir, target))
    try:
        matches = store.search(query, limit=limit)
    except Exception as exc:
        raise WorkspaceFsError(400, f"PPTX search failed: {exc}") from exc
    return PptxSearchResponse(matches=matches)


def pptx_export_pdf(*, user_id: str, uuid: str, path: str) -> PptxExportResponse:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = _resolve_pptx(workspace.files_dir, path)
    try:
        result = export_pptx_pdf(workspace=workspace, source_path=target)
    except Exception as exc:
        raise WorkspaceFsError(422, f"PPTX PDF export failed: {exc}") from exc
    return PptxExportResponse(**result)


def pptx_export_file(*, user_id: str, uuid: str, path: str) -> PptxExportResponse:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = _resolve_pptx(workspace.files_dir, path)
    try:
        result = export_pptx_file(workspace=workspace, source_path=target)
    except Exception as exc:
        raise WorkspaceFsError(422, f"PPTX export failed: {exc}") from exc
    return PptxExportResponse(**result)


def _resolve_pptx(files_dir: Path, path: str) -> Path:
    target = resolve_file(files_dir, path)
    if target.suffix.lower() != ".pptx":
        raise WorkspaceFsError(400, "Workspace file is not a PPTX file.")
    return target
