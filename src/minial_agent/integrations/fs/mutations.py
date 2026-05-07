import shutil
from pathlib import Path
from typing import Any

from minial_agent.integrations.fs.cache import (
    preview_cache_path,
    remove_preview_cache,
)
from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.fs.models import FsMutation
from minial_agent.integrations.fs.paths import (
    resolve_existing_path,
    resolve_public_path,
    validate_visible_name,
)
from minial_agent.integrations.fs.workspace import get_workspace
from minial_agent.integrations.upload import UploadRegistry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.visibility import physical_to_public_workspace_path


def create_file(
    *,
    user_id: str,
    uuid: str,
    path: str,
    content: str,
) -> FsMutation:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = resolve_public_path(workspace.files_dir, path)

    if target.exists():
        raise WorkspaceFsError(409, "Workspace file already exists.")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return FsMutation(
        path=physical_to_public_workspace_path(workspace.files_dir, target)
    )


def delete_file(*, user_id: str, uuid: str, path: str) -> FsMutation:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = resolve_public_path(workspace.files_dir, path)

    if not target.exists():
        raise WorkspaceFsError(404, "Workspace path not found.")

    public_path = physical_to_public_workspace_path(workspace.files_dir, target)
    registry = UploadRegistry(workspace.registry_path)
    affected_files = _affected_files(target)
    preview_dirs = [
        preview_cache_path(workspace.cache_dir, item) for item in affected_files
    ]
    if target.is_dir():
        registry_entries = registry.remove_by_visible_path_prefix(str(target))
        shutil.rmtree(target)
    else:
        registry_entries = registry.remove_by_visible_path(str(target))
        target.unlink()
    for preview_dir in preview_dirs:
        remove_preview_cache(preview_dir)
    for entry in registry_entries:
        _remove_converted_artifacts(workspace.converted_dir, entry)
    return FsMutation(path=public_path)


def move_path(
    *,
    user_id: str,
    uuid: str,
    path: str,
    destination_path: str,
) -> FsMutation:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    source = resolve_existing_path(workspace.files_dir, path)
    destination = resolve_public_path(workspace.files_dir, destination_path)
    _move_or_rename_path(workspace, source=source, destination=destination)
    return FsMutation(
        path=physical_to_public_workspace_path(workspace.files_dir, destination)
    )


def rename_path(
    *,
    user_id: str,
    uuid: str,
    path: str,
    name: str,
) -> FsMutation:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    source = resolve_existing_path(workspace.files_dir, path)
    validate_visible_name(name)
    destination = source.parent / name
    _move_or_rename_path(workspace, source=source, destination=destination)
    return FsMutation(
        path=physical_to_public_workspace_path(workspace.files_dir, destination)
    )


def _remove_converted_artifacts(
    converted_root: Path,
    registry_entry: dict[str, Any],
) -> None:
    converted_dir_value = registry_entry.get("converted_dir")
    if not isinstance(converted_dir_value, str) or not converted_dir_value:
        return

    converted_root_path = converted_root.resolve()
    converted_dir = Path(converted_dir_value).resolve()
    try:
        converted_dir.relative_to(converted_root_path)
    except ValueError:
        return
    shutil.rmtree(converted_dir, ignore_errors=True)


def _move_or_rename_path(
    workspace: UploadWorkspace,
    *,
    source: Path,
    destination: Path,
) -> None:
    source = source.resolve()
    destination = destination.resolve()
    files_root = workspace.files_dir.resolve()
    try:
        source.relative_to(files_root)
        destination.relative_to(files_root)
    except ValueError as exc:
        raise WorkspaceFsError(400, "Path is outside workspace.") from exc

    if source == files_root:
        raise WorkspaceFsError(400, "Workspace root cannot be moved or renamed.")
    if destination.exists():
        raise WorkspaceFsError(409, "Destination already exists.")
    if not destination.parent.is_dir():
        raise WorkspaceFsError(404, "Destination parent directory not found.")
    if source.is_dir():
        try:
            destination.relative_to(source)
        except ValueError:
            pass
        else:
            raise WorkspaceFsError(400, "Directory cannot be moved into itself.")

    affected_files = _affected_files(source)
    preview_dirs = [
        preview_cache_path(workspace.cache_dir, item) for item in affected_files
    ]
    shutil.move(str(source), str(destination))
    UploadRegistry(workspace.registry_path).update_visible_path_prefix(
        old_prefix=str(source),
        new_prefix=str(destination),
    )
    for preview_dir in preview_dirs:
        remove_preview_cache(preview_dir)


def _affected_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return [item for item in target.rglob("*") if item.is_file()]
    return []
