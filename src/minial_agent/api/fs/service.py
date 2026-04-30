from pathlib import Path

from fastapi import HTTPException, status

from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root
from minial_agent.integrations.upload.visibility import (
    WorkspaceVisibilityError,
    normalize_public_workspace_path,
    physical_to_public_workspace_path,
    public_virtual_to_physical,
)

from .schema import FsListItem, FsListResponse, FsMutationResponse


class FsService:
    def list_files(self, *, user_id: str, uuid: str, path: str = "/") -> FsListResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        directory = self._resolve_public_path(workspace.files_dir, path, allow_root=True)

        if not directory.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace path not found.",
            )
        if not directory.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace path is not a directory.",
            )

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

        return FsListResponse(
            path=physical_to_public_workspace_path(workspace.files_dir, directory),
            files=entries,
        )

    def create_file(
        self,
        *,
        user_id: str,
        uuid: str,
        path: str,
        content: str,
    ) -> FsMutationResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        target = self._resolve_public_path(workspace.files_dir, path)

        if target.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace file already exists.",
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return FsMutationResponse(
            path=physical_to_public_workspace_path(workspace.files_dir, target)
        )

    def delete_file(self, *, user_id: str, uuid: str, path: str) -> FsMutationResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        target = self._resolve_public_path(workspace.files_dir, path)

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace file not found.",
            )
        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only file deletion is supported.",
            )

        public_path = physical_to_public_workspace_path(workspace.files_dir, target)
        target.unlink()
        return FsMutationResponse(path=public_path)

    def _resolve_public_path(
        self,
        files_root: Path,
        path: str,
        *,
        allow_root: bool = False,
    ) -> Path:
        try:
            if allow_root and normalize_public_workspace_path(path, allow_root=True) == "/":
                return files_root.resolve()
            return public_virtual_to_physical(files_root, path)
        except WorkspaceVisibilityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc


fs_service = FsService()
