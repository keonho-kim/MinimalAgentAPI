import json
import zipfile
import importlib
from contextlib import asynccontextmanager
from pathlib import Path

import fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.processor.router import router as processor_router
from minial_agent.integrations.upload import ensure_upload_workspace
from minial_agent.integrations.upload import conversion
from minial_agent.integrations.upload.pipeline import UploadPipeline
from minial_agent.integrations.upload.xlsx import inspect_workbook


class FakeLockManager:
    def __init__(self) -> None:
        self.keys: list[str] = []

    @asynccontextmanager
    async def lock(self, workspace_key: str):
        self.keys.append(workspace_key)
        yield


def test_ensure_upload_workspace_creates_expected_layout(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)

    assert workspace.files_dir.is_dir()
    assert workspace.internal_outputs_dir.is_dir()
    assert workspace.registry_dir.is_dir()
    assert workspace.converted_dir.is_dir()
    assert workspace.jobs_dir.is_dir()
    assert workspace.cache_dir.is_dir()
    assert json.loads(workspace.registry_path.read_text()) == {"files": []}


def test_upload_pdf_creates_registry_manifest_and_page_image(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    response = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[
            (
                "files",
                ("sample.pdf", _make_pdf(), "application/pdf"),
            )
        ],
    )

    assert response.status_code == 200
    assert response.json() == {
        "uploaded_files": [
            {
                "file_id": "file_001",
                "filename": "sample.pdf",
                "file_type": "pdf",
                "status": "converted",
                "path": "files/sample.pdf",
                "error": None,
            }
        ]
    }

    workspace = tmp_path / "user"
    registry = json.loads((workspace / ".registry" / "files.json").read_text())
    assert registry["files"][0]["status"] == "converted"
    assert registry["files"][0]["manifest_path"].endswith(
        ".converted/file_001/manifest.json"
    )

    manifest_path = workspace / ".converted" / "file_001" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["status"] == "converted"
    assert manifest["converted_dir"].endswith(".converted/file_001")
    assert manifest["pages"][0]["image_filename"] == "page_001.png"
    assert (workspace / ".converted" / "file_001" / "pages" / "page_001.png").is_file()


def test_uploads_share_user_workspace_across_uuids(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    first = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "one"},
        files=[("files", ("one.pdf", _make_pdf(), "application/pdf"))],
    )
    second = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "two"},
        files=[("files", ("two.pdf", _make_pdf(), "application/pdf"))],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["uploaded_files"][0]["file_id"] == "file_001"
    assert second.json()["uploaded_files"][0]["file_id"] == "file_002"

    registry = json.loads((tmp_path / "user" / ".registry" / "files.json").read_text())
    assert [entry["visible_name"] for entry in registry["files"]] == [
        "one.pdf",
        "two.pdf",
    ]


def test_upload_response_uses_actual_unique_public_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    first = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[("files", ("sample.pdf", _make_pdf(), "application/pdf"))],
    )
    second = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[("files", ("sample.pdf", _make_pdf(), "application/pdf"))],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["uploaded_files"][0]["path"] == "files/sample.pdf"
    assert second.json()["uploaded_files"][0]["path"] == "files/sample_1.pdf"


def test_upload_preserves_original_unicode_filename(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    response = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[
            (
                "files",
                ("AX HUB 구축_제안요청서.pdf", _make_pdf(), "application/pdf"),
            )
        ],
    )

    assert response.status_code == 200
    uploaded = response.json()["uploaded_files"][0]
    assert uploaded["filename"] == "AX HUB 구축_제안요청서.pdf"
    assert uploaded["path"] == "files/AX HUB 구축_제안요청서.pdf"
    assert (tmp_path / "user" / "files" / "AX HUB 구축_제안요청서.pdf").is_file()


def test_upload_replaces_only_unsafe_filename_characters(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    response = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[
            (
                "files",
                ("AX:HUB?구축*.pdf", _make_pdf(), "application/pdf"),
            )
        ],
    )

    assert response.status_code == 200
    uploaded = response.json()["uploaded_files"][0]
    assert uploaded["filename"] == "AX_HUB_구축_.pdf"
    assert uploaded["path"] == "files/AX_HUB_구축_.pdf"


@pytest.mark.parametrize(
    ("source_extension", "target_extension", "media_type"),
    [
        ("ppt", "pptx", "application/vnd.ms-powerpoint"),
        ("doc", "docx", "application/msword"),
        ("xls", "xlsx", "application/vnd.ms-excel"),
    ],
)
def test_upload_legacy_office_converts_and_registers_ooxml(
    source_extension,
    target_extension,
    media_type,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    pipeline_module = importlib.import_module("minial_agent.integrations.upload.pipeline")

    def fake_convert_to_office_format(
        source_path: Path,
        output_dir: Path,
        target_path: Path,
        target_format: str,
    ) -> None:
        assert source_path.suffix == f".{source_extension}"
        assert target_path.suffix == f".{target_extension}"
        assert target_format == target_extension
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(target_extension.encode())

    def fake_build_upload_artifacts(**kwargs) -> None:
        converted_dir = kwargs["converted_dir"]
        converted_dir.mkdir(parents=True, exist_ok=True)
        (converted_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "file_id": kwargs["file_id"],
                    "source_filename": kwargs["source_path"].name,
                    "source_path": str(kwargs["source_path"]),
                    "file_type": kwargs["file_type"],
                    "converted_dir": str(converted_dir),
                    "pages": [],
                    "status": "converted",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        pipeline_module,
        "convert_to_office_format",
        fake_convert_to_office_format,
    )
    monkeypatch.setattr(pipeline_module, "build_upload_artifacts", fake_build_upload_artifacts)
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)
    router_module = importlib.import_module("minial_agent.api.processor.router")
    original_pipeline = router_module.processor_service.upload_pipeline
    router_module.processor_service.upload_pipeline = UploadPipeline()
    try:
        response = client.post(
            "/api/upload",
            data={"user_id": "user", "uuid": "session"},
            files=[
                (
                    "files",
                    (
                        f"legacy.{source_extension}",
                        source_extension.encode(),
                        media_type,
                    ),
                )
            ],
        )
    finally:
        router_module.processor_service.upload_pipeline = original_pipeline

    assert response.status_code == 200
    uploaded = response.json()["uploaded_files"][0]
    assert uploaded["filename"] == f"legacy.{target_extension}"
    assert uploaded["file_type"] == target_extension
    assert uploaded["path"] == f"files/legacy.{target_extension}"
    assert not (tmp_path / "user" / "files" / f"legacy.{source_extension}").exists()
    assert (tmp_path / "user" / "files" / f"legacy.{target_extension}").is_file()
    registry = json.loads((tmp_path / "user" / ".registry" / "files.json").read_text())
    assert registry["files"][0]["file_type"] == target_extension
    assert registry["files"][0]["visible_name"] == f"legacy.{target_extension}"


def test_upload_unsupported_extension_returns_per_file_failure(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    response = client.post(
        "/api/upload",
        data={"user_id": "user", "uuid": "session"},
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 200
    uploaded = response.json()["uploaded_files"][0]
    assert uploaded["file_id"] == "file_001"
    assert uploaded["filename"] == "notes.txt"
    assert uploaded["file_type"] == "txt"
    assert uploaded["status"] == "conversion_failed"
    assert uploaded["path"] is None
    assert "Unsupported file type" in uploaded["error"]


def test_upload_pipeline_locks_by_user_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    lock_manager = FakeLockManager()
    pipeline = UploadPipeline(lock_manager=lock_manager)
    app = FastAPI()
    app.include_router(processor_router)
    client = TestClient(app)

    router_module = importlib.import_module("minial_agent.api.processor.router")

    original_pipeline = router_module.processor_service.upload_pipeline
    router_module.processor_service.upload_pipeline = pipeline
    try:
        response = client.post(
            "/api/upload",
            data={"user_id": "user", "uuid": "session"},
            files=[("files", ("sample.pdf", _make_pdf(), "application/pdf"))],
        )
    finally:
        router_module.processor_service.upload_pipeline = original_pipeline

    assert response.status_code == 200
    assert lock_manager.keys == ["user"]


def test_render_pdf_pages_repairs_mupdf_structure_error(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\nbroken")
    calls: list[Path] = []

    def fake_render_once(path: Path, pages_dir: Path):
        calls.append(path)
        if len(calls) == 1:
            raise conversion.ConversionError(
                "Failed to render PDF page: MuPDF error: format error: "
                "No common ancestor in structure tree"
            )
        pages_dir.mkdir(parents=True, exist_ok=True)
        (pages_dir / "page_001.png").write_bytes(b"png")
        return [
            conversion.UploadedPage(
                page_number=1,
                image_filename="page_001.png",
                image_path=str(pages_dir / "page_001.png"),
            )
        ]

    def fake_repair(*, source_pdf: Path, repaired_pdf: Path) -> None:
        assert source_pdf == pdf_path
        repaired_pdf.write_bytes(b"%PDF-1.7\nrepaired")

    monkeypatch.setattr(conversion, "_render_pdf_pages_once", fake_render_once)
    monkeypatch.setattr(conversion, "_repair_pdf", fake_repair)

    pages = conversion.render_pdf_pages(pdf_path, tmp_path / "pages")

    assert [path.name for path in calls] == ["source.pdf", "source.repaired.pdf"]
    assert pages[0].image_filename == "page_001.png"
    assert not (tmp_path / "source.repaired.pdf").exists()


def test_inspect_workbook_reads_sheet_metadata(tmp_path) -> None:
    workbook_path = tmp_path / "book.xlsx"
    _write_minimal_xlsx(workbook_path)

    sheets = inspect_workbook(workbook_path)

    assert sheets == [
        {
            "sheet_name": "Summary",
            "visible": True,
            "used_range": "A1:B2",
            "headers": [],
            "sample_rows": [],
            "has_formulas": True,
            "formula_count": 1,
            "has_tables": False,
            "has_charts": False,
            "formula_summary": "1 formula(s). Examples: SUM(B1:B2)",
            "chart_summary": "No charts.",
            "text_summary": "",
        }
    ]


def _make_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "hello")
    data = document.tobytes()
    document.close()
    return data


def _write_minimal_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Summary" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:B2"/>
  <sheetData>
    <row r="1">
      <c r="A1"><f>SUM(B1:B2)</f><v>3</v></c>
    </row>
  </sheetData>
</worksheet>
""",
        )
