from pathlib import Path

from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.fs.models import FsList, FsListItem, FsSearch
from minial_agent.integrations.fs.paths import resolve_public_path
from minial_agent.integrations.fs.workspace import get_workspace
from minial_agent.integrations.upload.visibility import (
    WorkspaceVisibilityError,
    physical_to_public_workspace_path,
)


def list_files(*, user_id: str, uuid: str, path: str = "/") -> FsList:
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    directory = resolve_public_path(workspace.files_dir, path, allow_root=True)

    if not directory.exists():
        raise WorkspaceFsError(404, "Workspace path not found.")
    if not directory.is_dir():
        raise WorkspaceFsError(400, "Workspace path is not a directory.")

    entries = []
    for entry in sorted(
        directory.iterdir(),
        key=lambda item: (not item.is_dir(), item.name.lower()),
    ):
        if entry.name.startswith("."):
            continue
        stat = entry.stat()
        entries.append(
            FsListItem(
                name=entry.name,
                path=physical_to_public_workspace_path(workspace.files_dir, entry),
                type="directory" if entry.is_dir() else "file",
                size=None if entry.is_dir() else stat.st_size,
                modified_at=stat.st_mtime,
            )
        )

    return FsList(
        path=physical_to_public_workspace_path(workspace.files_dir, directory),
        files=entries,
    )


def search_files(
    *,
    user_id: str,
    uuid: str,
    query: str,
    limit: int = 10,
) -> FsSearch:
    normalized_query = query.strip().lower()
    workspace = get_workspace(user_id=user_id, uuid=uuid)
    max_results = min(max(limit, 1), 50)
    matches: list[tuple[tuple[int, bool, int, str], FsListItem]] = []

    for entry in workspace.files_dir.rglob("*"):
        if _has_hidden_part(entry.relative_to(workspace.files_dir)):
            continue
        if not entry.is_file():
            continue

        try:
            public_path = physical_to_public_workspace_path(workspace.files_dir, entry)
        except WorkspaceVisibilityError:
            continue

        name = entry.name
        name_lower = name.lower()
        path_lower = public_path.lower()
        if not normalized_query:
            rank = 0
        elif name_lower.startswith(normalized_query):
            rank = 0
        elif normalized_query in name_lower:
            rank = 1
        elif normalized_query in path_lower:
            rank = 2
        else:
            continue

        stat = entry.stat()
        matches.append(
            (
                (rank, name_lower != normalized_query, len(name), path_lower),
                FsListItem(
                    name=name,
                    path=public_path,
                    type="file",
                    size=stat.st_size,
                    modified_at=stat.st_mtime,
                ),
            )
        )

    return FsSearch(
        matches=[item for _, item in sorted(matches, key=lambda match: match[0])][
            :max_results
        ]
    )


def _has_hidden_part(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
