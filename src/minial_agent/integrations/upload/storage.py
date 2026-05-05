import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from starlette.datastructures import UploadFile

from minial_agent.integrations.upload.conversion import ConversionError
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.registry import UploadRegistry


SUPPORTED_FILE_TYPES = frozenset({"hwpx", "docx", "pptx", "xlsx", "pdf"})


@dataclass(frozen=True)
class UploadItem:
    file: UploadFile
    file_id: str
    filename: str
    file_type: str
    source_path: Path


def reserve_uploads(
    *,
    workspace: UploadWorkspace,
    files: Sequence[UploadFile],
) -> list[UploadItem]:
    registry = UploadRegistry(workspace.registry_path)
    next_file_number = _file_id_number(registry.next_file_id())
    reserved_paths = {
        Path(entry["visible_path"])
        for entry in registry.list_files()
        if entry.get("visible_path")
    }
    upload_items = []

    for index, file in enumerate(files):
        filename = safe_filename(file.filename or "uploaded_file")
        file_type = Path(filename).suffix.removeprefix(".").lower()
        source_path = unique_path(workspace.files_dir / filename, reserved_paths)
        file_id = f"file_{next_file_number + index:03d}"
        upload_items.append(
            UploadItem(
                file=file,
                file_id=file_id,
                filename=filename,
                file_type=file_type,
                source_path=source_path,
            )
        )

        if file_type in SUPPORTED_FILE_TYPES:
            converted_dir = workspace.converted_dir / file_id
            converted_dir.mkdir(parents=True, exist_ok=True)
            registry.add_uploaded(
                file_id=file_id,
                visible_path=source_path,
                visible_name=source_path.name,
                file_type=file_type,
                converted_dir=converted_dir,
            )

    return upload_items


async def save_upload_file(file: UploadFile, source_path: Path) -> None:
    with source_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)
    await file.close()


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip()
    return name or "uploaded_file"


def unique_path(path: Path, reserved_paths: set[Path] | None = None) -> Path:
    reserved_paths = reserved_paths if reserved_paths is not None else set()
    if not path.exists() and path not in reserved_paths:
        reserved_paths.add(path)
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists() and candidate not in reserved_paths:
            reserved_paths.add(candidate)
            return candidate
    raise ConversionError(f"Could not allocate a unique filename for {path.name}")


def _file_id_number(file_id: str) -> int:
    try:
        return int(file_id.removeprefix("file_"))
    except ValueError as exc:
        raise ConversionError(f"Invalid upload file id: {file_id}") from exc
