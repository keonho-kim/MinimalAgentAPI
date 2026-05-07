from pathlib import Path

from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.fs.paths import validate_output_part
from minial_agent.integrations.fs.workspace import get_workspace


def output_file_path(
    *,
    user_id: str,
    uuid: str,
    job_id: str,
    filename: str,
) -> Path:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    validate_output_part(job_id, label="job_id")
    validate_output_part(filename, label="filename")
    return existing_output_path(
        workspace.internal_outputs_dir / job_id / "files" / filename,
        outputs_root=workspace.internal_outputs_dir,
    )


def output_bundle_path(*, user_id: str, uuid: str, job_id: str) -> Path:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    validate_output_part(job_id, label="job_id")
    return existing_output_path(
        workspace.internal_outputs_dir / job_id / "result.zip",
        outputs_root=workspace.internal_outputs_dir,
    )


def existing_output_path(path: Path, *, outputs_root: Path) -> Path:
    resolved_root = outputs_root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceFsError(400, "Output path is outside the workspace.") from exc

    if not resolved_path.is_file():
        raise WorkspaceFsError(404, "Output file not found.")
    return resolved_path
