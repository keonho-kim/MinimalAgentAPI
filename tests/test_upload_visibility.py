import json

from deepagents.backends.filesystem import FilesystemBackend
from openpyxl import Workbook, load_workbook
import pytest

from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.read import (
    build_docx_read_workflow,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pdf.agent import (
    build_pdf_subagent,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.agent import (
    build_xlsx_subagent,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.edit import (
    build_xlsx_edit_workflow,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.read import (
    build_xlsx_read_workflow,
)
from minial_agent.common.utils import file_registry
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
    _register_converted_file(
        workspace,
        filename="report.docx",
        file_type="docx",
        page_count=3,
    )
    scanned_pages = []

    workflow = build_docx_read_workflow(
        workspace,
        page_scanner=lambda path, _question: (
            scanned_pages.append(path.name) or "1; matched page"
            if path.name == "page_002.png"
            else scanned_pages.append(path.name) or "0; no_evidence"
        ),
    )
    result = workflow.invoke(
        {
            "file_ref": "file_001",
            "question": "summary?",
        }
    )
    payload = json.loads(result["result"])

    assert payload["relevant_page_count"] == 1
    assert payload["scanned_pages"] == 3
    assert set(scanned_pages) == {"page_001.png", "page_002.png", "page_003.png"}
    assert payload["relevant_pages"][0]["page_number"] == 2
    assert payload["relevant_pages"][0]["evidence"] == "matched page"
    assert payload["answer"].startswith("관련 근거는 report.docx의 2페이지")
    assert ".converted" not in result["result"]
    assert ".registry" not in result["result"]


def test_workflow_rejects_malformed_page_scan(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    _register_converted_file(workspace, filename="report.docx", file_type="docx")

    graph = build_docx_read_workflow(
        workspace,
        page_scanner=lambda _path, _question: "invalid",
    )

    with pytest.raises(ValueError, match="Invalid VLM scan output"):
        graph.invoke(
            {
                "file_ref": "file_001",
                "question": "summary?",
            }
        )


def test_workflow_edits_xlsx_and_registers_new_file(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    source_path = workspace.files_dir / "book.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "old"
    workbook.save(source_path)
    workbook.close()
    converted_dir = workspace.converted_dir / "file_001"
    converted_dir.mkdir()
    (converted_dir / "manifest.json").write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "book.xlsx",
                "source_path": str(source_path),
                "file_type": "xlsx",
                "pdf_path": str(converted_dir / "source.pdf"),
                "pages": [],
                "status": "converted",
            }
        ),
        encoding="utf-8",
    )
    registry = UploadRegistry(workspace.registry_path)
    registry.add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="book.xlsx",
        file_type="xlsx",
        converted_dir=converted_dir,
    )
    registry.update_status("file_001", status="converted")

    def fake_build_upload_artifacts(**kwargs):
        target_dir = kwargs["converted_dir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "file_id": kwargs["file_id"],
                    "source_filename": kwargs["source_path"].name,
                    "file_type": kwargs["file_type"],
                    "pages": [],
                    "status": "converted",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(file_registry, "build_upload_artifacts", fake_build_upload_artifacts)
    graph = build_xlsx_edit_workflow(
        workspace,
        operation_selector=lambda _instruction: "write_values",
        slot_filler=lambda _operation, _instruction: "SHEET=Summary; CELL=A1; VALUE=new",
    )

    result = graph.invoke(
        {
            "file_ref": "file_001",
            "instruction": "SHEET=Summary; CELL=A1; VALUE=new",
        }
    )
    payload = json.loads(result["result"])

    assert payload["edited_file"]["file_id"] == "file_002"
    assert payload["edited_file"]["download_url"].startswith("/api/fs/outputs/")
    assert ".outputs" not in result["result"]
    assert ".converted" not in result["result"]
    assert (workspace.files_dir / "book_edited.xlsx").is_file()

    edited = load_workbook(workspace.files_dir / "book_edited.xlsx")
    try:
        assert edited["Summary"]["A1"].value == "new"
    finally:
        edited.close()


def test_xlsx_read_workflow_uses_workbook_sheet_summary(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    source_path = workspace.files_dir / "book.xlsx"
    source_path.write_text("xlsx", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    summary_sheet_dir = converted_dir / "xlsx" / "sheets" / "sheet_0001"
    detail_sheet_dir = converted_dir / "xlsx" / "sheets" / "sheet_0002"
    summary_sheet_dir.mkdir(parents=True)
    detail_sheet_dir.mkdir(parents=True)
    (converted_dir / "manifest.json").write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "book.xlsx",
                "source_path": str(source_path),
                "file_type": "xlsx",
                "pdf_path": str(converted_dir / "source.pdf"),
                "pages": [],
                "status": "converted",
            }
        ),
        encoding="utf-8",
    )
    (converted_dir / "workbook_index.json").write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "book.xlsx",
                "sheet_count": 2,
                "sheets": [
                    {
                        "sheet_id": "sheet_0001",
                        "sheet_name": "Summary",
                        "index": 0,
                        "visible": True,
                        "used_range": "A1:B2",
                        "has_formulas": False,
                        "formula_count": 0,
                        "sheet_summary_path": str(summary_sheet_dir / "sheet.json"),
                    },
                    {
                        "sheet_id": "sheet_0002",
                        "sheet_name": "Detail",
                        "index": 1,
                        "visible": True,
                        "used_range": "A1:B2",
                        "has_formulas": False,
                        "formula_count": 0,
                        "sheet_summary_path": str(detail_sheet_dir / "sheet.json"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (summary_sheet_dir / "sheet.json").write_text(
        json.dumps(
            {
                "sheet_id": "sheet_0001",
                "sheet_name": "Summary",
                "index": 0,
                "visible": True,
                "used_range": "A1:B2",
                "headers": ["Metric", "Value"],
                "sample_rows": [["Revenue", 10]],
                "formula_summary": "",
                "chart_summary": "",
                "text_summary": "Revenue summary",
                "pages": [
                    {
                        "page_number": 1,
                        "image_filename": "summary_page_001.png",
                        "image_path": str(summary_sheet_dir / "pages" / "page_001.png"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (detail_sheet_dir / "sheet.json").write_text(
        json.dumps(
            {
                "sheet_id": "sheet_0002",
                "sheet_name": "Detail",
                "index": 1,
                "visible": True,
                "used_range": "A1:B2",
                "headers": ["Metric", "Value"],
                "sample_rows": [["Expense", 5]],
                "formula_summary": "",
                "chart_summary": "",
                "text_summary": "Expense summary",
                "pages": [
                    {
                        "page_number": 1,
                        "image_filename": "detail_page_001.png",
                        "image_path": str(detail_sheet_dir / "pages" / "page_001.png"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    registry = UploadRegistry(workspace.registry_path)
    registry.add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="book.xlsx",
        file_type="xlsx",
        converted_dir=converted_dir,
    )
    registry.update_status("file_001", status="converted")

    scanned_pages = []
    graph = build_xlsx_read_workflow(
        workspace,
        sheet_mapper=lambda summary, _question: (
            "1; A1:B2; revenue evidence"
            if summary["sheet_name"] == "Summary"
            else "0; no_range; no_evidence"
        ),
        page_scanner=lambda path, _question: (
            scanned_pages.append(path.name) or "1; rendered revenue page"
        ),
    )
    result = graph.invoke(
        {
            "file_ref": "file_001",
            "question": "revenue?",
        }
    )
    payload = json.loads(result["result"])

    assert payload["relevant_sheet_count"] == 1
    assert payload["relevant_sheets"][0]["sheet_name"] == "Summary"
    assert payload["relevant_sheets"][0]["candidate_ranges"] == "A1:B2"
    assert payload["scanned_pages"] == 1
    assert scanned_pages == ["page_001.png"]
    assert payload["relevant_pages"][0]["filename"] == "summary_page_001.png"
    assert payload["answer"].startswith("관련 근거는 book.xlsx의 1페이지")
    assert ".converted" not in result["result"]


def test_xlsx_read_workflow_rejects_malformed_sheet_scan(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    source_path = workspace.files_dir / "book.xlsx"
    source_path.write_text("xlsx", encoding="utf-8")
    converted_dir = workspace.converted_dir / "file_001"
    sheet_dir = converted_dir / "xlsx" / "sheets" / "sheet_0001"
    sheet_dir.mkdir(parents=True)
    (converted_dir / "manifest.json").write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "book.xlsx",
                "source_path": str(source_path),
                "file_type": "xlsx",
                "pdf_path": str(converted_dir / "source.pdf"),
                "pages": [],
                "status": "converted",
            }
        ),
        encoding="utf-8",
    )
    (converted_dir / "workbook_index.json").write_text(
        json.dumps(
            {
                "file_id": "file_001",
                "source_filename": "book.xlsx",
                "sheet_count": 1,
                "sheets": [
                    {
                        "sheet_id": "sheet_0001",
                        "sheet_name": "Summary",
                        "index": 0,
                        "visible": True,
                        "used_range": "A1:B2",
                        "has_formulas": False,
                        "formula_count": 0,
                        "sheet_summary_path": str(sheet_dir / "sheet.json"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (sheet_dir / "sheet.json").write_text(
        json.dumps(
            {
                "sheet_id": "sheet_0001",
                "sheet_name": "Summary",
                "index": 0,
                "visible": True,
                "used_range": "A1:B2",
            }
        ),
        encoding="utf-8",
    )
    registry = UploadRegistry(workspace.registry_path)
    registry.add_uploaded(
        file_id="file_001",
        visible_path=source_path,
        visible_name="book.xlsx",
        file_type="xlsx",
        converted_dir=converted_dir,
    )
    registry.update_status("file_001", status="converted")

    graph = build_xlsx_read_workflow(
        workspace,
        sheet_mapper=lambda _summary, _question: "invalid",
    )

    with pytest.raises(ValueError, match="Invalid XLSX sheet scan output"):
        graph.invoke(
            {
                "file_ref": "file_001",
                "question": "revenue?",
            }
        )


def test_pdf_worker_exposes_read_only_tool() -> None:
    tool_names = [tool.name for tool in build_pdf_subagent()["tools"]]

    assert tool_names == ["answer_pdf_question"]


def test_xlsx_worker_exposes_answer_and_edit_tools_only() -> None:
    tool_names = [tool.name for tool in build_xlsx_subagent()["tools"]]

    assert tool_names == ["answer_xlsx_question", "edit_xlsx"]


def _register_converted_file(
    workspace,
    *,
    filename: str,
    file_type: str,
    page_count: int = 1,
) -> None:
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
                        "page_number": index,
                        "image_filename": f"page_{index:03d}.png",
                        "image_path": str(converted_dir / "pages" / f"page_{index:03d}.png"),
                    }
                    for index in range(1, page_count + 1)
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
