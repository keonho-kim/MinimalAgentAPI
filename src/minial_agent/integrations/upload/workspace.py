import os
import shutil
from pathlib import Path

from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.storage import unique_path


REGISTRY_FILENAME = "files.json"
INTERNAL_DIR_NAMES = frozenset(
    {".registry", ".converted", ".jobs", ".cache", ".outputs", ".agents"}
)


def ensure_upload_workspace(root_dir: str | Path) -> UploadWorkspace:
    root = Path(root_dir)
    workspace = UploadWorkspace(
        root=root,
        files_dir=root / "files",
        internal_outputs_dir=root / ".outputs",
        registry_dir=root / ".registry",
        converted_dir=root / ".converted",
        jobs_dir=root / ".jobs",
        cache_dir=root / ".cache",
        agents_dir=root / ".agents",
        skills_dir=root / ".agents" / "skills",
        registry_path=root / ".registry" / REGISTRY_FILENAME,
    )

    for directory in (
        workspace.root,
        workspace.files_dir,
        workspace.internal_outputs_dir,
        workspace.registry_dir,
        workspace.converted_dir,
        workspace.jobs_dir,
        workspace.cache_dir,
        workspace.agents_dir,
        workspace.skills_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    if not workspace.registry_path.exists():
        workspace.registry_path.write_text('{"files": []}\n', encoding="utf-8")

    _migrate_legacy_public_entries(workspace)

    return workspace


def get_workspace_root(user_id: str, uuid: str) -> Path:
    _validate_path_part(user_id)
    _validate_path_part(uuid)

    base_dir = Path(os.getenv("AGENT_RUNTIME_ROOT_DIR", "./tmpWorkspace"))
    return base_dir / user_id


def _validate_path_part(value: str) -> None:
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValueError(f"Invalid workspace path value: {value}")


def _migrate_legacy_public_entries(workspace: UploadWorkspace) -> None:
    reserved_paths = set(workspace.files_dir.iterdir())

    legacy_outputs_dir = workspace.root / "outputs"
    if legacy_outputs_dir.is_dir():
        for entry in legacy_outputs_dir.iterdir():
            target = unique_path(workspace.files_dir / entry.name, reserved_paths)
            shutil.move(str(entry), target)
        try:
            legacy_outputs_dir.rmdir()
        except OSError:
            pass

    for entry in workspace.root.iterdir():
        if entry.name in INTERNAL_DIR_NAMES or entry.name == workspace.files_dir.name:
            continue
        target = unique_path(workspace.files_dir / entry.name, reserved_paths)
        shutil.move(str(entry), target)
