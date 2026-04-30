import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import UploadWorkspace
from .registry import UploadRegistry
from .visibility import (
    WorkspaceVisibilityError,
    normalize_public_workspace_path,
    physical_to_public_workspace_path,
    public_virtual_to_physical,
)


class UploadArtifactResolutionError(ValueError):
    """Raised when an uploaded file cannot be resolved to internal artifacts."""


@dataclass(frozen=True)
class ResolvedUploadArtifact:
    workspace_root: Path
    file_id: str
    visible_name: str
    file_type: str
    status: str
    source_path: Path
    converted_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]
    workbook_index_path: Path | None = None
    workbook_index: dict[str, Any] | None = None

    def public_metadata(self) -> dict[str, Any]:
        pages = self.manifest.get("pages", [])
        metadata = {
            "file_id": self.file_id,
            "filename": self.visible_name,
            "file_type": self.file_type,
            "status": self.status,
            "visible_path": physical_to_public_workspace_path(self.workspace_root, self.source_path),
            "page_count": len(pages) if isinstance(pages, list) else 0,
        }
        if self.workbook_index:
            metadata["sheet_count"] = self.workbook_index.get("sheet_count", 0)
        return metadata


def resolve_upload_artifact(
    *,
    workspace: UploadWorkspace,
    file_ref: str,
    expected_file_type: str | None = None,
) -> ResolvedUploadArtifact:
    entry = _find_registry_entry(workspace=workspace, file_ref=file_ref)
    file_id = str(entry.get("file_id", ""))
    file_type = str(entry.get("file_type", "")).lower()
    status = str(entry.get("status", ""))

    if expected_file_type and file_type != expected_file_type.lower():
        raise UploadArtifactResolutionError(
            f"Expected a {expected_file_type} file, but {file_ref} is {file_type}."
        )
    if status != "converted":
        raise UploadArtifactResolutionError(
            f"File {file_ref} is not ready. Current status: {status or 'unknown'}."
        )

    source_path = Path(str(entry.get("visible_path", ""))).resolve()
    converted_dir = Path(str(entry.get("converted_dir", ""))).resolve()
    manifest_path = Path(str(entry.get("manifest_path", ""))).resolve()

    _assert_internal_path(workspace, converted_dir)
    _assert_internal_path(workspace, manifest_path)

    if not manifest_path.exists():
        raise UploadArtifactResolutionError(f"Manifest not found for {file_ref}.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    workbook_index_path = converted_dir / "workbook_index.json"
    workbook_index = None
    if workbook_index_path.exists():
        workbook_index = json.loads(workbook_index_path.read_text(encoding="utf-8"))

    return ResolvedUploadArtifact(
        workspace_root=workspace.files_dir,
        file_id=file_id,
        visible_name=str(entry.get("visible_name", source_path.name)),
        file_type=file_type,
        status=status,
        source_path=source_path,
        converted_dir=converted_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        workbook_index_path=workbook_index_path if workbook_index else None,
        workbook_index=workbook_index,
    )


def _find_registry_entry(
    *,
    workspace: UploadWorkspace,
    file_ref: str,
) -> dict[str, Any]:
    registry = UploadRegistry(workspace.registry_path)
    entries = registry.list_files()

    for entry in entries:
        if entry.get("file_id") == file_ref:
            return entry

    try:
        requested_path = public_virtual_to_physical(workspace.files_dir, file_ref)
    except WorkspaceVisibilityError as exc:
        raise UploadArtifactResolutionError(str(exc)) from exc

    requested_name = requested_path.name
    for entry in entries:
        visible_path = Path(str(entry.get("visible_path", ""))).resolve()
        if visible_path == requested_path:
            return entry
        if entry.get("visible_name") == requested_name:
            return entry

    normalized_ref = normalize_public_workspace_path(file_ref)
    raise UploadArtifactResolutionError(f"Uploaded file not found: {normalized_ref}")


def _assert_internal_path(workspace: UploadWorkspace, path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(workspace.converted_dir.resolve())
    except ValueError as exc:
        raise UploadArtifactResolutionError(
            "Artifact path is outside the converted workspace."
        ) from exc
