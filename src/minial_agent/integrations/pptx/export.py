from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

from minial_agent.integrations.upload.artifacts import build_upload_artifacts
from minial_agent.integrations.upload.conversion import convert_to_pdf
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.registry import UploadRegistry
from minial_agent.integrations.upload.storage import unique_path


def export_pptx_pdf(
    *,
    workspace: UploadWorkspace,
    source_path: Path,
) -> dict[str, str]:
    output_dir = workspace.cache_dir / "exports" / uuid4().hex[:12]
    pdf_path = output_dir / f"{source_path.stem}.pdf"
    convert_to_pdf(source_path, output_dir / ".pdf", pdf_path)
    return _register_export(
        workspace=workspace,
        source_path=source_path,
        export_path=pdf_path,
        file_type="pdf",
    )


def export_pptx_file(
    *,
    workspace: UploadWorkspace,
    source_path: Path,
) -> dict[str, str]:
    export_path = workspace.cache_dir / "exports" / uuid4().hex[:12] / source_path.name
    export_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, export_path)
    return _register_export(
        workspace=workspace,
        source_path=source_path,
        export_path=export_path,
        file_type="pptx",
    )


def _register_export(
    *,
    workspace: UploadWorkspace,
    source_path: Path,
    export_path: Path,
    file_type: str,
) -> dict[str, str]:
    job_id = f"job_{uuid4().hex[:12]}"
    output_dir = workspace.internal_outputs_dir / job_id
    output_files_dir = output_dir / "files"
    output_files_dir.mkdir(parents=True, exist_ok=True)
    output_name = export_path.name
    output_path = output_files_dir / output_name
    shutil.copyfile(export_path, output_path)

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
        file_type=file_type,
        converted_dir=converted_dir,
    )
    build_upload_artifacts(
        source_path=visible_path,
        file_id=file_id,
        file_type=file_type,
        converted_dir=converted_dir,
        cache_dir=workspace.cache_dir,
    )
    registry.update_status(file_id, status="converted")

    manifest = {
        "job_id": job_id,
        "source_path": str(source_path),
        "exported_file_id": file_id,
        "files": [output_name],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(output_dir / "result.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(output_path, f"files/{output_name}")
        bundle.write(output_dir / "manifest.json", "manifest.json")

    return {
        "file_id": file_id,
        "filename": visible_path.name,
        "download_url": f"/api/fs/outputs/{job_id}/files/{output_name}",
        "job_id": job_id,
    }
