import json
from pathlib import Path
from typing import Any


class UploadRegistry:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path

    def list_files(self) -> list[dict[str, Any]]:
        return list(self._read()["files"])

    def next_file_id(self) -> str:
        max_number = 0
        for item in self.list_files():
            file_id = str(item.get("file_id", ""))
            if not file_id.startswith("file_"):
                continue
            try:
                max_number = max(max_number, int(file_id.removeprefix("file_")))
            except ValueError:
                continue
        return f"file_{max_number + 1:03d}"

    def add_uploaded(
        self,
        *,
        file_id: str,
        visible_path: Path,
        visible_name: str,
        file_type: str,
        converted_dir: Path,
    ) -> dict[str, Any]:
        entry = {
            "file_id": file_id,
            "visible_path": str(visible_path),
            "visible_name": visible_name,
            "file_type": file_type,
            "status": "uploaded",
            "converted_dir": str(converted_dir),
            "manifest_path": str(converted_dir / "manifest.json"),
        }
        data = self._read()
        data["files"].append(entry)
        self._write(data)
        return entry

    def update_status(
        self,
        file_id: str,
        *,
        status: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        data = self._read()
        for entry in data["files"]:
            if entry.get("file_id") != file_id:
                continue
            entry["status"] = status
            if error:
                entry["error"] = error
            else:
                entry.pop("error", None)
            self._write(data)
            return entry
        raise KeyError(f"Unknown upload file_id: {file_id}")

    def lookup(
        self,
        *,
        file_id: str | None = None,
        visible_path: str | None = None,
    ) -> dict[str, Any] | None:
        for entry in self.list_files():
            if file_id and entry.get("file_id") == file_id:
                return entry
            if visible_path and entry.get("visible_path") == visible_path:
                return entry
        return None

    def remove_by_visible_path(self, visible_path: str) -> list[dict[str, Any]]:
        data = self._read()
        removed = [
            entry
            for entry in data["files"]
            if entry.get("visible_path") == visible_path
        ]
        if not removed:
            return []

        data["files"] = [
            entry
            for entry in data["files"]
            if entry.get("visible_path") != visible_path
        ]
        self._write(data)
        return removed

    def remove_by_visible_path_prefix(self, visible_path: str) -> list[dict[str, Any]]:
        data = self._read()
        prefix = _path_prefix(visible_path)
        removed = [
            entry
            for entry in data["files"]
            if _path_matches_prefix(str(entry.get("visible_path", "")), prefix)
        ]
        if not removed:
            return []

        data["files"] = [
            entry
            for entry in data["files"]
            if not _path_matches_prefix(str(entry.get("visible_path", "")), prefix)
        ]
        self._write(data)
        return removed

    def update_visible_path_prefix(
        self,
        *,
        old_prefix: str,
        new_prefix: str,
    ) -> list[dict[str, Any]]:
        data = self._read()
        old_normalized = _path_prefix(old_prefix)
        new_normalized = _path_prefix(new_prefix)
        updated: list[dict[str, Any]] = []

        for entry in data["files"]:
            visible_path = str(entry.get("visible_path", ""))
            if not _path_matches_prefix(visible_path, old_normalized):
                continue

            suffix = visible_path[len(old_normalized) :]
            if suffix.startswith(("/", "\\")):
                suffix = suffix[1:]
            next_path = str(Path(new_normalized) / suffix) if suffix else new_normalized
            entry["visible_path"] = next_path
            entry["visible_name"] = Path(next_path).name
            updated.append(dict(entry))

        if updated:
            self._write(data)
        return updated

    def _read(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"files": []}
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if "files" not in data or not isinstance(data["files"], list):
            raise ValueError(f"Invalid upload registry: {self.registry_path}")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        temp_path = self.registry_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.registry_path)


def _path_prefix(value: str) -> str:
    return str(Path(value).resolve() if Path(value).is_absolute() else Path(value))


def _path_matches_prefix(value: str, prefix: str) -> bool:
    if value == prefix:
        return True
    return value.startswith(f"{prefix}/") or value.startswith(f"{prefix}\\")
