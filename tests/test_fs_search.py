from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.fs.router import router as fs_router
from minial_agent.integrations.fs.cache import preview_cache_dir
from minial_agent.integrations.upload import ensure_upload_workspace
from minial_agent.integrations.upload.registry import UploadRegistry


def test_list_files_returns_public_directory_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "report.pdf").write_text("pdf", encoding="utf-8")
    nested = workspace.files_dir / "nested"
    nested.mkdir()
    (workspace.files_dir / ".hidden.pdf").write_text("hidden", encoding="utf-8")

    response = _client().get(
        "/api/fs/list",
        params={"user_id": "user", "uuid": "session"},
    )

    assert response.status_code == 200
    assert response.json()["path"] == "files"
    assert [
        (item["name"], item["path"], item["type"])
        for item in response.json()["files"]
    ] == [
        ("nested", "files/nested", "directory"),
        ("report.pdf", "files/report.pdf", "file"),
    ]


def test_list_files_lists_nested_public_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    nested = workspace.files_dir / "nested"
    nested.mkdir()
    (nested / "report.pdf").write_text("pdf", encoding="utf-8")

    response = _client().get(
        "/api/fs/list",
        params={"user_id": "user", "uuid": "session", "path": "files/nested"},
    )

    assert response.status_code == 200
    assert response.json()["path"] == "files/nested"
    assert [
        (item["name"], item["path"], item["type"])
        for item in response.json()["files"]
    ] == [("report.pdf", "files/nested/report.pdf", "file")]


def test_search_files_returns_visible_recursive_matches(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "report.docx").write_text("doc", encoding="utf-8")
    nested = workspace.files_dir / "nested"
    nested.mkdir()
    (nested / "quarterly_report.pdf").write_text("pdf", encoding="utf-8")
    (nested / "notes.txt").write_text("notes", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "user", "uuid": "session", "q": "report"},
    )

    assert response.status_code == 200
    assert [item["path"] for item in response.json()["matches"]] == [
        "files/report.docx",
        "files/nested/quarterly_report.pdf",
    ]


def test_search_files_matches_public_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    nested = workspace.files_dir / "reports"
    nested.mkdir()
    (nested / "summary.txt").write_text("summary", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "user", "uuid": "session", "q": "reports"},
    )

    assert response.status_code == 200
    assert [item["path"] for item in response.json()["matches"]] == [
        "files/reports/summary.txt",
    ]


def test_search_files_hides_dot_paths_and_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "secret-report.txt").mkdir()
    (workspace.files_dir / ".secret-report.txt").write_text("hidden", encoding="utf-8")
    hidden_dir = workspace.files_dir / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "secret-report.txt").write_text("hidden", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "user", "uuid": "session", "q": "secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"matches": []}


def test_search_files_returns_visible_recursive_files_for_blank_query(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "report.docx").write_text("doc", encoding="utf-8")
    nested = workspace.files_dir / "nested"
    nested.mkdir()
    (nested / "notes.txt").write_text("notes", encoding="utf-8")
    (workspace.files_dir / ".hidden.pdf").write_text("hidden", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "user", "uuid": "session", "q": "  "},
    )

    assert response.status_code == 200
    assert [item["path"] for item in response.json()["matches"]] == [
        "files/nested/notes.txt",
        "files/report.docx",
    ]


def test_search_files_isolated_by_user_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "report.docx").write_text("doc", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "other-user", "uuid": "session", "q": "report"},
    )

    assert response.status_code == 200
    assert response.json() == {"matches": []}


def test_delete_file_removes_registry_and_converted_artifacts(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    source_path = workspace.files_dir / "report.pdf"
    source_path.write_text("pdf", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    (converted_dir / "manifest.json").write_text("{}", encoding="utf-8")
    preview_dir = preview_cache_dir(
        workspace.cache_dir,
        source_path,
    )
    (preview_dir / "source.pdf").write_text("pdf", encoding="utf-8")
    UploadRegistry(workspace.registry_path).add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="report.pdf",
        file_type="pdf",
        converted_dir=converted_dir,
    )

    response = _client().delete(
        "/api/fs/files",
        params={
            "user_id": "user",
            "uuid": "session",
            "path": "files/report.pdf",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"path": "files/report.pdf"}
    assert not source_path.exists()
    assert not converted_dir.exists()
    assert not preview_dir.exists()
    assert UploadRegistry(workspace.registry_path).list_files() == []


def test_delete_file_without_registry_removes_visible_file(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    source_path = workspace.files_dir / "notes.txt"
    source_path.write_text("notes", encoding="utf-8")

    response = _client().delete(
        "/api/fs/files",
        params={
            "user_id": "user",
            "uuid": "session",
            "path": "files/notes.txt",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"path": "files/notes.txt"}
    assert not source_path.exists()


def test_delete_directory_removes_registry_and_converted_artifacts(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    directory = workspace.files_dir / "reports"
    directory.mkdir()
    source_path = directory / "report.pdf"
    source_path.write_text("pdf", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    (converted_dir / "manifest.json").write_text("{}", encoding="utf-8")
    preview_dir = preview_cache_dir(
        workspace.cache_dir,
        source_path,
    )
    (preview_dir / "source.pdf").write_text("pdf", encoding="utf-8")
    UploadRegistry(workspace.registry_path).add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="report.pdf",
        file_type="pdf",
        converted_dir=converted_dir,
    )

    response = _client().delete(
        "/api/fs/files",
        params={
            "user_id": "user",
            "uuid": "session",
            "path": "files/reports",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"path": "files/reports"}
    assert not directory.exists()
    assert not converted_dir.exists()
    assert not preview_dir.exists()
    assert UploadRegistry(workspace.registry_path).list_files() == []


def test_rename_file_updates_registry_and_clears_preview_cache(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    source_path = workspace.files_dir / "report.pdf"
    source_path.write_text("pdf", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    preview_dir = preview_cache_dir(
        workspace.cache_dir,
        source_path,
    )
    (preview_dir / "source.pdf").write_text("pdf", encoding="utf-8")
    UploadRegistry(workspace.registry_path).add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="report.pdf",
        file_type="pdf",
        converted_dir=converted_dir,
    )

    response = _client().post(
        "/api/fs/rename",
        json={
            "user_id": "user",
            "uuid": "session",
            "path": "files/report.pdf",
            "name": "renamed.pdf",
        },
    )

    renamed_path = workspace.files_dir / "renamed.pdf"
    entries = UploadRegistry(workspace.registry_path).list_files()
    assert response.status_code == 200
    assert response.json() == {"path": "files/renamed.pdf"}
    assert renamed_path.is_file()
    assert not source_path.exists()
    assert converted_dir.exists()
    assert not preview_dir.exists()
    assert entries[0]["visible_path"] == str(renamed_path)
    assert entries[0]["visible_name"] == "renamed.pdf"


def test_move_directory_updates_nested_registry_entries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    source_dir = workspace.files_dir / "reports"
    source_dir.mkdir()
    target_root = workspace.files_dir / "archive"
    target_root.mkdir()
    source_path = source_dir / "report.pdf"
    source_path.write_text("pdf", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    UploadRegistry(workspace.registry_path).add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="report.pdf",
        file_type="pdf",
        converted_dir=converted_dir,
    )

    response = _client().post(
        "/api/fs/move",
        json={
            "user_id": "user",
            "uuid": "session",
            "path": "files/reports",
            "destination_path": "files/archive/reports",
        },
    )

    moved_path = target_root / "reports" / "report.pdf"
    entries = UploadRegistry(workspace.registry_path).list_files()
    assert response.status_code == 200
    assert response.json() == {"path": "files/archive/reports"}
    assert moved_path.is_file()
    assert not source_dir.exists()
    assert converted_dir.exists()
    assert entries[0]["visible_path"] == str(moved_path)
    assert entries[0]["visible_name"] == "report.pdf"


def test_move_file_rejects_conflict(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "source.txt").write_text("source", encoding="utf-8")
    (workspace.files_dir / "target.txt").write_text("target", encoding="utf-8")

    response = _client().post(
        "/api/fs/move",
        json={
            "user_id": "user",
            "uuid": "session",
            "path": "files/source.txt",
            "destination_path": "files/target.txt",
        },
    )

    assert response.status_code == 409


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(fs_router)
    return TestClient(app)
