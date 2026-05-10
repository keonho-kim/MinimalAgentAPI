import json
import mimetypes
from pathlib import Path

from minial_agent.integrations.fs.cache import preview_cache_dir
from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.fs.models import FsPreview
from minial_agent.integrations.fs.paths import resolve_file
from minial_agent.integrations.fs.workspace import get_workspace
from minial_agent.integrations.upload.conversion import ConversionError, convert_to_pdf
from minial_agent.integrations.upload.visibility import physical_to_public_workspace_path
from minial_agent.integrations.upload.xlsx import build_xlsx_preview
from minial_agent.integrations.pptx.preview import build_pptx_preview


SOURCE_PREVIEW_TYPES = {
    "bash": "code",
    "cjs": "code",
    "css": "code",
    "go": "code",
    "htm": "code",
    "html": "code",
    "java": "code",
    "js": "code",
    "json": "code",
    "jsx": "code",
    "mjs": "code",
    "pdf": "pdf",
    "py": "code",
    "docx": "office_pdf",
    "pptx": "office_pdf",
    "hwpx": "hwpx",
    "md": "markdown",
    "markdown": "markdown",
    "sh": "code",
    "sql": "code",
    "txt": "text",
    "ts": "code",
    "tsx": "code",
    "zsh": "code",
}
SUPPORTED_PREVIEW_TYPES = SOURCE_PREVIEW_TYPES | {"xlsx": "xlsx_grid"}


def preview_file(*, user_id: str, uuid: str, path: str) -> FsPreview:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = resolve_file(workspace.files_dir, path)
    public_path = physical_to_public_workspace_path(workspace.files_dir, target)
    file_type = target.suffix.removeprefix(".").lower()
    preview_type = SUPPORTED_PREVIEW_TYPES.get(file_type)
    if not preview_type:
        raise WorkspaceFsError(
            415,
            f"Preview is not supported for .{file_type or 'unknown'} files.",
        )

    if preview_type == "xlsx_grid":
        return FsPreview(
            path=public_path,
            filename=target.name,
            file_type=file_type,
            preview_type=preview_type,
            workbook=xlsx_preview(workspace.cache_dir, target),
        )

    if preview_type == "office_pdf":
        office_pdf_path(workspace.cache_dir, target)
        presentation = (
            pptx_preview(workspace.cache_dir, target)
            if file_type == "pptx"
            else None
        )
        return FsPreview(
            path=public_path,
            filename=target.name,
            file_type=file_type,
            preview_type=preview_type,
            presentation=presentation,
        )

    return FsPreview(
        path=public_path,
        filename=target.name,
        file_type=file_type,
        preview_type=preview_type,
    )


def preview_source_path(*, user_id: str, uuid: str, path: str) -> Path:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    target = resolve_file(workspace.files_dir, path)
    file_type = target.suffix.removeprefix(".").lower()
    preview_type = SOURCE_PREVIEW_TYPES.get(file_type)
    if not preview_type:
        raise WorkspaceFsError(
            415,
            f"Preview source is not supported for .{file_type or 'unknown'} files.",
        )
    if preview_type == "office_pdf":
        return office_pdf_path(workspace.cache_dir, target)
    return target


def preview_source_media_type(path: Path) -> str:
    file_type = path.suffix.removeprefix(".").lower()
    if file_type == "hwpx":
        return "application/vnd.hancom.hwpx"
    if file_type in {"md", "markdown"}:
        return "text/markdown; charset=utf-8"
    if file_type == "txt":
        return "text/plain; charset=utf-8"
    if SOURCE_PREVIEW_TYPES.get(file_type) == "code":
        return "text/plain; charset=utf-8"
    if file_type == "pdf":
        return "application/pdf"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def office_pdf_path(cache_dir: Path, source_path: Path) -> Path:
    preview_dir = preview_cache_dir(cache_dir, source_path)
    pdf_path = preview_dir / "source.pdf"
    if pdf_path.is_file():
        return pdf_path

    output_dir = preview_dir / ".pdf"
    try:
        convert_to_pdf(source_path, output_dir, pdf_path)
    except ConversionError as exc:
        raise WorkspaceFsError(422, f"Failed to build preview PDF: {exc}") from exc
    return pdf_path


def xlsx_preview(cache_dir: Path, source_path: Path) -> dict:
    preview_dir = preview_cache_dir(cache_dir, source_path)
    preview_path = preview_dir / "workbook.json"
    if preview_path.is_file():
        return json.loads(preview_path.read_text(encoding="utf-8"))

    try:
        workbook = build_xlsx_preview(source_path)
    except Exception as exc:
        raise WorkspaceFsError(422, f"Failed to build XLSX preview: {exc}") from exc
    preview_path.write_text(
        json.dumps(workbook, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return workbook


def pptx_preview(cache_dir: Path, source_path: Path) -> dict:
    preview_dir = preview_cache_dir(cache_dir, source_path)
    preview_path = preview_dir / "presentation.json"
    if preview_path.is_file():
        return json.loads(preview_path.read_text(encoding="utf-8"))

    try:
        presentation = build_pptx_preview(source_path)
    except Exception as exc:
        raise WorkspaceFsError(422, f"Failed to inspect PPTX: {exc}") from exc
    preview_path.write_text(
        json.dumps(presentation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return presentation
