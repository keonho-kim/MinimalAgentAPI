import asyncio
from pathlib import Path
from typing import Sequence

from starlette.datastructures import UploadFile

from minial_agent.common.locks import WorkspaceLockManager, workspace_lock_manager

from .artifacts import build_upload_artifacts
from .models import UploadedFileResult, UploadWorkspace
from .registry import UploadRegistry
from .storage import (
    SUPPORTED_FILE_TYPES,
    UploadItem,
    reserve_uploads,
    save_upload_file,
)
from .workspace import ensure_upload_workspace, get_workspace_root


class UploadPipeline:
    def __init__(
        self,
        conversion_max_concurrency: int = 3,
        lock_manager: WorkspaceLockManager | None = None,
    ) -> None:
        self.conversion_max_concurrency = conversion_max_concurrency
        self._registry_locks: dict[Path, asyncio.Lock] = {}
        self.lock_manager = lock_manager or workspace_lock_manager

    async def upload_files(
        self,
        *,
        user_id: str,
        uuid: str,
        files: Sequence[UploadFile],
    ) -> list[UploadedFileResult]:
        async with self.lock_manager.lock(user_id):
            workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
            semaphore = asyncio.Semaphore(self.conversion_max_concurrency)
            registry_lock = self._registry_lock(workspace.registry_path)
            async with registry_lock:
                upload_items = reserve_uploads(workspace=workspace, files=files)

            async def upload_one(item: UploadItem) -> UploadedFileResult:
                async with semaphore:
                    return await self._process_file(
                        item=item,
                        workspace=workspace,
                        registry_lock=registry_lock,
                    )

            return await asyncio.gather(*(upload_one(item) for item in upload_items))

    async def _process_file(
        self,
        *,
        item: UploadItem,
        workspace: UploadWorkspace,
        registry_lock: asyncio.Lock,
    ) -> UploadedFileResult:
        registry = UploadRegistry(workspace.registry_path)

        if item.file_type not in SUPPORTED_FILE_TYPES:
            await item.file.close()
            return UploadedFileResult(
                file_id=item.file_id,
                filename=item.filename,
                file_type=item.file_type,
                status="conversion_failed",
                error=f"Unsupported file type: {item.file_type or 'unknown'}",
            )

        converted_dir = workspace.converted_dir / item.file_id

        try:
            await save_upload_file(item.file, item.source_path)
            await asyncio.to_thread(
                build_upload_artifacts,
                source_path=item.source_path,
                file_id=item.file_id,
                file_type=item.file_type,
                converted_dir=converted_dir,
                cache_dir=workspace.cache_dir,
            )
            async with registry_lock:
                registry.update_status(item.file_id, status="converted")
            return UploadedFileResult(
                file_id=item.file_id,
                filename=item.source_path.name,
                file_type=item.file_type,
                status="converted",
            )
        except Exception as exc:
            error = str(exc)
            async with registry_lock:
                registry.update_status(
                    item.file_id,
                    status="conversion_failed",
                    error=error,
                )
            return UploadedFileResult(
                file_id=item.file_id,
                filename=item.source_path.name,
                file_type=item.file_type,
                status="conversion_failed",
                error=error,
            )

    def _registry_lock(self, registry_path: Path) -> asyncio.Lock:
        key = registry_path.resolve()
        lock = self._registry_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._registry_locks[key] = lock
        return lock
