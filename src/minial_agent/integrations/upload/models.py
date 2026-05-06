from dataclasses import dataclass
from pathlib import Path
from typing import Literal


UploadStatus = Literal["uploaded", "converted", "conversion_failed"]


@dataclass(frozen=True)
class UploadWorkspace:
    root: Path
    files_dir: Path
    internal_outputs_dir: Path
    registry_dir: Path
    converted_dir: Path
    jobs_dir: Path
    cache_dir: Path
    agents_dir: Path
    skills_dir: Path
    registry_path: Path


@dataclass(frozen=True)
class UploadedFileResult:
    file_id: str
    filename: str
    file_type: str
    status: UploadStatus
    error: str | None = None


@dataclass(frozen=True)
class UploadedPage:
    page_number: int
    image_filename: str
    image_path: str
