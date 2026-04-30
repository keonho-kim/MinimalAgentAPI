import json

from deepagents.backends.filesystem import FilesystemBackend

from minial_agent.agents.domain.office_file_agent.subagents.utils.workflow import (
    build_office_file_workflow,
)
from minial_agent.integrations.upload import ensure_upload_workspace
from minial_agent.integrations.upload.registry import UploadRegistry
from minial_agent.integrations.upload.resolver import resolve_upload_artifact
from minial_agent.integrations.upload.visibility import (
    WorkspaceVisibilityError,
    normalize_public_workspace_path,
    to_public_workspace_path,
)


def test_normalize_public_workspace_path_rejects_internal_paths() -> None:
    assert normalize_public_workspace_path("/workspace/files/report.docx") == (
        "/report.docx"
    )
    assert normalize_public_workspace_path("report.docx") == "/report.docx"
    assert to_public_workspace_path("/result.docx") == "files/result.docx"

    for hidden_path in (
        "/workspace/.registry/files.json",
        ".converted/file_001/manifest.json",
        "/files/.secret",
        "/workspace/outputs/result.docx",
    ):
        try:
            normalize_public_workspace_path(hidden_path)
        except WorkspaceVisibilityError:
            continue
        raise AssertionError(f"Expected hidden path rejection: {hidden_path}")


def test_filesystem_backend_rooted_at_files_hides_internal_directories(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    (workspace.files_dir / "report.txt").write_text("hello", encoding="utf-8")
    (workspace.registry_dir / "secret.txt").write_text("secret", encoding="utf-8")

    backend = FilesystemBackend(
        root_dir=workspace.files_dir,
        virtual_mode=True,
        max_file_size_mb=1024,
    )

    root_entries = backend.ls("/").entries or []
    assert [entry["path"] for entry in root_entries] == ["/report.txt"]
    assert backend.read("/report.txt").error is None
    assert backend.read("/.registry/secret.txt").error is not None
    assert backend.grep("secret", "/").matches == []
    glob_matches = backend.glob("**/*", "/").matches or []
    assert [match["path"] for match in glob_matches] == ["/report.txt"]


def test_resolver_returns_public_metadata_without_internal_paths(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    source_path = workspace.files_dir / "report.docx"
    source_path.write_text("doc", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    manifest_path = converted_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "report.docx",
                "source_path": str(source_path),
                "file_type": "docx",
                "pdf_path": str(converted_dir / "source.pdf"),
                "pages": [
                    {
                        "page_number": 1,
                        "image_filename": "page_001.png",
                        "image_path": str(converted_dir / "pages" / "page_001.png"),
                    }
                ],
                "status": "converted",
            }
        ),
        encoding="utf-8",
    )
    registry = UploadRegistry(workspace.registry_path)
    registry.add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="report.docx",
        file_type="docx",
        converted_dir=converted_dir,
    )
    registry.update_status("file_001", status="converted")

    artifact = resolve_upload_artifact(
        workspace=workspace,
        file_ref="/workspace/files/report.docx",
        expected_file_type="docx",
    )
    metadata = artifact.public_metadata()

    assert metadata == {
        "file_id": "file_001",
        "filename": "report.docx",
        "file_type": "docx",
        "status": "converted",
        "visible_path": "files/report.docx",
        "page_count": 1,
    }
    assert ".converted" not in json.dumps(metadata)
    assert ".registry" not in json.dumps(metadata)


def test_workflow_result_does_not_expose_internal_paths(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    _register_converted_file(workspace, filename="report.docx", file_type="docx")

    workflow = build_office_file_workflow(workspace)
    result = workflow.invoke(
        {
            "file_ref": "file_001",
            "file_type": "docx",
            "operation": "answer",
            "question": "summary?",
        }
    )

    assert "DOCX question answering workflow resolved" in result["result"]
    assert ".converted" not in result["result"]
    assert ".registry" not in result["result"]


def _register_converted_file(workspace, *, filename: str, file_type: str) -> None:
    source_path = workspace.files_dir / filename
    source_path.write_text("doc", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    manifest_path = converted_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": filename,
                "source_path": str(source_path),
                "file_type": file_type,
                "pdf_path": str(converted_dir / "source.pdf"),
                "pages": [
                    {
                        "page_number": 1,
                        "image_filename": "page_001.png",
                        "image_path": str(converted_dir / "pages" / "page_001.png"),
                    }
                ],
                "status": "converted",
            }
        ),
        encoding="utf-8",
    )
    registry = UploadRegistry(workspace.registry_path)
    registry.add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name=filename,
        file_type=file_type,
        converted_dir=converted_dir,
    )
    registry.update_status("file_001", status="converted")
