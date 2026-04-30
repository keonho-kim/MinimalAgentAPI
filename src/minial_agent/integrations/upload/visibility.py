from pathlib import Path, PurePosixPath


FILES_DIR_NAME = "files"
INTERNAL_OUTPUTS_DIR_NAME = ".outputs"
REGISTRY_DIR_NAME = ".registry"
CONVERTED_DIR_NAME = ".converted"
JOBS_DIR_NAME = ".jobs"
CACHE_DIR_NAME = ".cache"

PUBLIC_DIRS = frozenset({FILES_DIR_NAME})
INTERNAL_DIRS = frozenset(
    {
        INTERNAL_OUTPUTS_DIR_NAME,
        REGISTRY_DIR_NAME,
        CONVERTED_DIR_NAME,
        JOBS_DIR_NAME,
        CACHE_DIR_NAME,
    }
)


class WorkspaceVisibilityError(ValueError):
    """Raised when a path attempts to access hidden workspace data."""


def normalize_public_workspace_path(
    path: str | Path,
    *,
    default_dir: str = FILES_DIR_NAME,
    allow_root: bool = False,
) -> str:
    """Return a normalized virtual path rooted at the public files workspace."""
    if default_dir != FILES_DIR_NAME:
        raise ValueError(f"Invalid default public directory: {default_dir}")

    raw_path = str(path).strip()
    if not raw_path:
        if allow_root:
            return "/"
        raise WorkspaceVisibilityError("Empty workspace path is not allowed")

    normalized = _strip_legacy_public_prefix(raw_path)
    if normalized in {"", ".", "/"}:
        if allow_root:
            return "/"
        raise WorkspaceVisibilityError("Workspace root is not a file path")

    parts = _path_parts(normalized)
    if not parts:
        if allow_root:
            return "/"
        raise WorkspaceVisibilityError("Workspace root is not a file path")

    _reject_private_parts(parts)
    return "/" + "/".join(parts)


def is_public_workspace_path(path: str | Path) -> bool:
    try:
        normalize_public_workspace_path(path, allow_root=True)
    except WorkspaceVisibilityError:
        return False
    return True


def to_public_workspace_path(path: str | Path) -> str:
    """Render a public path for display in the UI file drawer."""
    normalized = normalize_public_workspace_path(path, allow_root=True)
    if normalized == "/":
        return FILES_DIR_NAME
    return f"{FILES_DIR_NAME}{normalized}"


def public_virtual_to_physical(files_root: Path, path: str | Path) -> Path:
    """Resolve a UI/agent-visible path to a physical path under files_root."""
    normalized = normalize_public_workspace_path(path)
    resolved_root = files_root.resolve()
    resolved_path = (resolved_root / normalized.lstrip("/")).resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceVisibilityError("Path is outside workspace") from exc
    return resolved_path


def physical_to_public_workspace_path(files_root: Path, path: str | Path) -> str:
    resolved_root = files_root.resolve()
    resolved_path = Path(path).resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceVisibilityError("Path is outside workspace") from exc

    return to_public_workspace_path("/" + relative.as_posix())


def is_internal_workspace_path(path: str | Path) -> bool:
    raw_path = str(path).strip()
    if not raw_path:
        return False
    normalized = _strip_legacy_public_prefix(raw_path)
    parts = _path_parts(normalized)
    return any(part in INTERNAL_DIRS or part.startswith(".") for part in parts)


def _strip_legacy_public_prefix(path: str) -> str:
    path = path.replace("\\", "/")
    legacy_prefixes = (
        "/workspace/files/",
        "workspace/files/",
        "/files/",
        "files/",
    )
    legacy_roots = {
        "/workspace",
        "workspace",
        "/workspace/files",
        "workspace/files",
        "/files",
        "files",
    }

    if path in legacy_roots:
        return "/"
    for prefix in legacy_prefixes:
        if path.startswith(prefix):
            return "/" + path.removeprefix(prefix)

    if path in {"/workspace/outputs", "workspace/outputs", "/outputs", "outputs"}:
        raise WorkspaceVisibilityError("Outputs are internal workspace paths")
    if path.startswith(("/workspace/outputs/", "workspace/outputs/", "/outputs/", "outputs/")):
        raise WorkspaceVisibilityError("Outputs are internal workspace paths")

    return path


def _path_parts(path: str) -> list[str]:
    posix = PurePosixPath(path)
    return [part for part in posix.parts if part not in {"", "/"}]


def _reject_private_parts(parts: list[str]) -> None:
    for part in parts:
        if part in {"..", "~"} or part.startswith("~"):
            raise WorkspaceVisibilityError("Path traversal is not allowed")
        if part in INTERNAL_DIRS or part.startswith("."):
            raise WorkspaceVisibilityError(
                "Internal workspace paths are not visible to the user or agent"
            )
