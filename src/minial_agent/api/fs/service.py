import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException, status

from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root
from minial_agent.integrations.upload.conversion import ConversionError, convert_to_pdf
from minial_agent.integrations.upload.visibility import (
    WorkspaceVisibilityError,
    normalize_public_workspace_path,
    physical_to_public_workspace_path,
    public_virtual_to_physical,
)
from minial_agent.integrations.upload.xlsx import build_xlsx_preview

from minial_agent.api.fs.schema import (
    FsListItem,
    FsListResponse,
    FsMutationResponse,
    FsPreviewResponse,
    FsSearchResponse,
)


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

    def search_files(
        self,
        *,
        user_id: str,
        uuid: str,
        query: str,
        limit: int = 10,
    ) -> FsSearchResponse:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return FsSearchResponse(matches=[])

        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        max_results = min(max(limit, 1), 50)
        matches: list[tuple[tuple[int, bool, int, str], FsListItem]] = []

        for entry in workspace.files_dir.rglob("*"):
            if self._has_hidden_part(entry.relative_to(workspace.files_dir)):
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
            if name_lower.startswith(normalized_query):
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

        return FsSearchResponse(
            matches=[item for _, item in sorted(matches, key=lambda match: match[0])][
                :max_results
            ]
        )

    def preview_file(self, *, user_id: str, uuid: str, path: str) -> FsPreviewResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        target = self._resolve_file(workspace.files_dir, path)
        public_path = physical_to_public_workspace_path(workspace.files_dir, target)
        file_type = target.suffix.removeprefix(".").lower()
        preview_type = SUPPORTED_PREVIEW_TYPES.get(file_type)
        if not preview_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Preview is not supported for .{file_type or 'unknown'} files.",
            )

        source_url = self._preview_source_url(
            user_id=user_id,
            uuid=uuid,
            path=public_path,
        )
        if preview_type == "xlsx_grid":
            return FsPreviewResponse(
                path=public_path,
                filename=target.name,
                file_type=file_type,
                preview_type=preview_type,
                workbook=self._xlsx_preview(workspace.cache_dir, target),
            )

        if preview_type == "office_pdf":
            self._office_pdf_path(workspace.cache_dir, target)

        return FsPreviewResponse(
            path=public_path,
            filename=target.name,
            file_type=file_type,
            preview_type=preview_type,
            source_url=source_url,
        )

    def preview_source_path(self, *, user_id: str, uuid: str, path: str) -> Path:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        target = self._resolve_file(workspace.files_dir, path)
        file_type = target.suffix.removeprefix(".").lower()
        preview_type = SOURCE_PREVIEW_TYPES.get(file_type)
        if not preview_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Preview source is not supported for .{file_type or 'unknown'} files.",
            )
        if preview_type == "office_pdf":
            return self._office_pdf_path(workspace.cache_dir, target)
        return target

    def preview_source_media_type(self, path: Path) -> str:
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

    def output_file_path(
        self,
        *,
        user_id: str,
        uuid: str,
        job_id: str,
        filename: str,
    ) -> Path:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        self._validate_output_part(job_id, label="job_id")
        self._validate_output_part(filename, label="filename")
        return self._existing_output_path(
            workspace.internal_outputs_dir / job_id / "files" / filename,
            outputs_root=workspace.internal_outputs_dir,
        )

    def output_bundle_path(self, *, user_id: str, uuid: str, job_id: str) -> Path:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        self._validate_output_part(job_id, label="job_id")
        return self._existing_output_path(
            workspace.internal_outputs_dir / job_id / "result.zip",
            outputs_root=workspace.internal_outputs_dir,
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

    def _resolve_file(self, files_root: Path, path: str) -> Path:
        target = self._resolve_public_path(files_root, path)
        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace file not found.",
            )
        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace path is not a file.",
            )
        return target

    def _preview_source_url(self, *, user_id: str, uuid: str, path: str) -> str:
        return f"/api/fs/preview/source?{urlencode({'user_id': user_id, 'uuid': uuid, 'path': path})}"

    def _existing_output_path(self, path: Path, *, outputs_root: Path) -> Path:
        resolved_root = outputs_root.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Output path is outside the workspace.",
            ) from exc

        if not resolved_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Output file not found.",
            )
        return resolved_path

    def _validate_output_part(self, value: str, *, label: str) -> None:
        if not value or Path(value).name != value or value in {".", ".."}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid output {label}.",
            )

    def _office_pdf_path(self, cache_dir: Path, source_path: Path) -> Path:
        preview_dir = self._preview_cache_dir(cache_dir, source_path)
        pdf_path = preview_dir / "source.pdf"
        if pdf_path.is_file():
            return pdf_path

        output_dir = preview_dir / ".pdf"
        try:
            convert_to_pdf(source_path, output_dir, pdf_path)
        except ConversionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to build preview PDF: {exc}",
            ) from exc
        return pdf_path

    def _xlsx_preview(self, cache_dir: Path, source_path: Path) -> dict:
        preview_dir = self._preview_cache_dir(cache_dir, source_path)
        preview_path = preview_dir / "workbook.json"
        if preview_path.is_file():
            return json.loads(preview_path.read_text(encoding="utf-8"))

        try:
            workbook = build_xlsx_preview(source_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to build XLSX preview: {exc}",
            ) from exc
        preview_path.write_text(
            json.dumps(workbook, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return workbook

    def _preview_cache_dir(self, cache_dir: Path, source_path: Path) -> Path:
        stat = source_path.stat()
        key_source = f"{source_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
        key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]
        preview_dir = cache_dir / "previews" / key
        preview_dir.mkdir(parents=True, exist_ok=True)
        return preview_dir

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

    def _has_hidden_part(self, path: Path) -> bool:
        return any(part.startswith(".") for part in path.parts)


fs_service = FsService()
