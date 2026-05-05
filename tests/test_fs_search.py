from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.fs.router import router as fs_router
from minial_agent.integrations.upload import ensure_upload_workspace


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


def test_search_files_returns_empty_for_blank_query(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    (workspace.files_dir / "report.docx").write_text("doc", encoding="utf-8")

    response = _client().get(
        "/api/fs/search",
        params={"user_id": "user", "uuid": "session", "q": "  "},
    )

    assert response.status_code == 200
    assert response.json() == {"matches": []}


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


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(fs_router)
    return TestClient(app)
