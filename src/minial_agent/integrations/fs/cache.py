import hashlib
import shutil
from pathlib import Path


def preview_cache_dir(cache_dir: Path, source_path: Path) -> Path:
    preview_dir = preview_cache_path(cache_dir, source_path)
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir


def preview_cache_path(cache_dir: Path, source_path: Path) -> Path:
    stat = source_path.stat()
    key_source = f"{source_path.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
    key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]
    return cache_dir / "previews" / key


def remove_preview_cache(preview_dir: Path) -> None:
    shutil.rmtree(preview_dir, ignore_errors=True)
