from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class FsListItem:
    name: str
    path: str
    type: Literal["directory", "file"]
    size: int | None = None
    modified_at: float | None = None


@dataclass(frozen=True)
class FsList:
    path: str
    files: list[FsListItem]


@dataclass(frozen=True)
class FsSearch:
    matches: list[FsListItem]


@dataclass(frozen=True)
class FsPreview:
    path: str
    filename: str
    file_type: str
    preview_type: str
    workbook: dict[str, Any] | None = None


@dataclass(frozen=True)
class FsMutation:
    path: str
