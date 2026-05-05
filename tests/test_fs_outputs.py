import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.fs.router import router as fs_router
from minial_agent.integrations.upload import ensure_upload_workspace


def test_download_output_file_and_bundle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    workspace = ensure_upload_workspace(tmp_path / "user")
    output_dir = workspace.internal_outputs_dir / "job_123"
    files_dir = output_dir / "files"
    files_dir.mkdir(parents=True)
    (files_dir / "result.txt").write_text("done", encoding="utf-8")
    bundle_path = output_dir / "result.zip"
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("files/result.txt", "done")

    client = _client()

    file_response = client.get(
        "/api/fs/outputs/job_123/files/result.txt",
        params={"user_id": "user", "uuid": "session"},
    )
    bundle_response = client.get(
        "/api/fs/outputs/job_123/result.zip",
        params={"user_id": "user", "uuid": "session"},
    )

    assert file_response.status_code == 200
    assert file_response.text == "done"
    assert bundle_response.status_code == 200
    assert bundle_response.content.startswith(b"PK")


def test_download_output_rejects_path_traversal(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))

    response = _client().get(
        "/api/fs/outputs/../files/result.txt",
        params={"user_id": "user", "uuid": "session"},
    )

    assert response.status_code in {400, 404}


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(fs_router)
    return TestClient(app)
