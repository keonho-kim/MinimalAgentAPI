import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from minial_agent.integrations.upload.artifacts import build_upload_artifacts
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.registry import UploadRegistry
from minial_agent.integrations.upload.resolver import (
    ResolvedUploadArtifact,
    resolve_upload_artifact,
)
from minial_agent.integrations.upload.storage import unique_path


@dataclass(frozen=True)
class EditedFileResult:
    file_id: str
    filename: str
    download_url: str
    job_id: str


def resolve_artifact(
    *,
    workspace: UploadWorkspace,
    file_ref: str,
    expected_file_type: str | None = None,
) -> ResolvedUploadArtifact:
    return resolve_upload_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type=expected_file_type,
    )


def register_edited_file(
    *,
    workspace: UploadWorkspace,
    source_artifact: ResolvedUploadArtifact,
    edited_path: Path,
    changed_items: list[dict],
) -> tuple[EditedFileResult, dict]:
    job_id = f"job_{uuid4().hex[:12]}"
    output_dir = workspace.internal_outputs_dir / job_id
    output_files_dir = output_dir / "files"
    output_files_dir.mkdir(parents=True, exist_ok=True)

    output_name = edited_path.name
    output_path = output_files_dir / output_name
    shutil.copyfile(edited_path, output_path)

    visible_path = unique_path(workspace.files_dir / output_name)
    shutil.copyfile(output_path, visible_path)

    registry = UploadRegistry(workspace.registry_path)
    file_id = registry.next_file_id()
    converted_dir = workspace.converted_dir / file_id
    converted_dir.mkdir(parents=True, exist_ok=True)
    registry.add_uploaded(
        file_id=file_id,
        visible_path=visible_path,
        visible_name=visible_path.name,
        file_type=source_artifact.file_type,
        converted_dir=converted_dir,
    )
    try:
        build_upload_artifacts(
            source_path=visible_path,
            file_id=file_id,
            file_type=source_artifact.file_type,
            converted_dir=converted_dir,
            cache_dir=workspace.cache_dir,
        )
        registry.update_status(file_id, status="converted")
    except Exception as exc:
        registry.update_status(file_id, status="conversion_failed", error=str(exc))
        raise

    manifest = {
        "job_id": job_id,
        "source_file_id": source_artifact.file_id,
        "edited_file_id": file_id,
        "files": [output_name],
        "changed_items": changed_items,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_output_bundle(output_dir)

    result = EditedFileResult(
        file_id=file_id,
        filename=visible_path.name,
        download_url=f"/api/fs/outputs/{job_id}/files/{output_name}",
        job_id=job_id,
    )
    return result, manifest


def _write_output_bundle(output_dir: Path) -> None:
    with zipfile.ZipFile(output_dir / "result.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in (output_dir / "files").iterdir():
            if path.is_file():
                bundle.write(path, f"files/{path.name}")
        manifest_path = output_dir / "manifest.json"
        if manifest_path.is_file():
            bundle.write(manifest_path, "manifest.json")
