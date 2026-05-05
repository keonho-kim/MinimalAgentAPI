import json
import zipfile
from pathlib import Path

import pytest
from docx import Document
from openpyxl import Workbook, load_workbook
from pptx import Presentation

from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.utils.editing import (
    apply_docx_edit,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.edit.nodes import (
    build_docx_edit_spec,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_hwpx.utils.editing import (
    apply_hwpx_edit,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.utils.editing import (
    apply_pptx_edit,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.utils.editing import (
    apply_xlsx_edit,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.workflow.edit import (
    build_xlsx_edit_workflow,
)
from minial_agent.agents.domain.office_file_agent.subagents.utils.edit_protocol import (
    parse_slots,
    select_operation,
)
from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload import ensure_upload_workspace
from minial_agent.integrations.upload.registry import UploadRegistry


def test_edit_protocol_rejects_malformed_outputs() -> None:
    with pytest.raises(ValueError, match="one line"):
        select_operation(
            instruction="edit",
            prompt="{instruction}",
            selector=lambda _instruction: "replace_text\nextra",
        )

    with pytest.raises(ValueError, match="JSON or markdown"):
        parse_slots('{"OLD_TEXT": "a"}')

    with pytest.raises(ValueError, match="KEY=VALUE"):
        parse_slots("OLD_TEXT=a; bad_segment")

    with pytest.raises(ValueError, match="non-empty"):
        parse_slots("OLD_TEXT=a; NEW_TEXT=")


def test_docx_edit_operations_change_file(tmp_path) -> None:
    path = tmp_path / "report.docx"
    document = Document()
    document.add_paragraph("FY2024 revenue")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "old cell"
    document.save(path)

    replace_result = apply_docx_edit(
        path=path,
        operation="replace_text",
        slots={"OLD_TEXT": "FY2024", "NEW_TEXT": "FY2025"},
        source_filename="report.docx",
    )
    add_result = apply_docx_edit(
        path=path,
        operation="add_paragraph",
        slots={"TEXT": "new paragraph"},
        source_filename="report.docx",
    )
    table_result = apply_docx_edit(
        path=path,
        operation="update_table_cell",
        slots={"TABLE": "1", "ROW": "1", "COLUMN": "1", "TEXT": "new cell"},
        source_filename="report.docx",
    )

    edited = Document(path)
    assert edited.paragraphs[0].text == "FY2025 revenue"
    assert edited.paragraphs[-1].text == "new paragraph"
    assert edited.tables[0].cell(0, 0).text == "new cell"
    assert replace_result[0]["changed_count"] == 1
    assert add_result[0]["changed_count"] == 1
    assert table_result[0]["changed_count"] == 1


def test_docx_edit_rejects_missing_slot() -> None:
    with pytest.raises(ValueError, match="NEW_TEXT"):
        build_docx_edit_spec(
            instruction="replace",
            operation_selector=lambda _instruction: "replace_text",
            slot_filler=lambda _operation, _instruction: "OLD_TEXT=FY2024",
        )


def test_pptx_edit_operations_change_file(tmp_path) -> None:
    path = tmp_path / "deck.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Old title"
    slide.placeholders[1].text = "Old body"
    presentation.save(path)

    apply_pptx_edit(
        path=path,
        operation="replace_slide_title",
        slots={"PAGE": "1", "TITLE": "New title"},
        source_filename="deck.pptx",
    )
    apply_pptx_edit(
        path=path,
        operation="replace_slide_text",
        slots={"PAGE": "1", "OLD_TEXT": "Old body", "TEXT": "New body"},
        source_filename="deck.pptx",
    )
    add_result = apply_pptx_edit(
        path=path,
        operation="add_slide",
        slots={"TITLE": "Added slide", "TEXT": "Added body"},
        source_filename="deck.pptx",
    )

    edited = Presentation(path)
    assert edited.slides[0].shapes.title.text == "New title"
    assert edited.slides[0].placeholders[1].text == "New body"
    assert edited.slides[1].shapes.title.text == "Added slide"
    assert add_result[0]["page_number"] == 2


def test_xlsx_edit_operations_change_file(tmp_path) -> None:
    path = tmp_path / "book.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "old"
    workbook.save(path)
    workbook.close()

    apply_xlsx_edit(
        path=path,
        operation="write_values",
        slots={"SHEET": "Summary", "START_CELL": "A1", "END_CELL": "B2", "VALUES": "1,2|3,4"},
        source_filename="book.xlsx",
    )
    apply_xlsx_edit(
        path=path,
        operation="write_formulas",
        slots={
            "SHEET": "Summary",
            "START_CELL": "C2",
            "END_CELL": "C3",
            "FORMULA_PATTERN": 'IFERROR((B{row}-B{prev_row})/B{prev_row},"")',
        },
        source_filename="book.xlsx",
    )
    apply_xlsx_edit(
        path=path,
        operation="add_sheet",
        slots={"SHEET": "NewSheet", "CELL": "A1", "VALUE": "created"},
        source_filename="book.xlsx",
    )
    format_result = apply_xlsx_edit(
        path=path,
        operation="format_range",
        slots={"SHEET": "Summary", "RANGE": "A1:B2", "FILL": "FFFF00", "BOLD": "true"},
        source_filename="book.xlsx",
    )

    edited = load_workbook(path)
    try:
        assert edited["Summary"]["A1"].value == "1"
        assert edited["Summary"]["B2"].value == "4"
        assert edited["Summary"]["C2"].value == '=IFERROR((B2-B1)/B1,"")'
        assert edited["Summary"]["C3"].value == '=IFERROR((B3-B2)/B2,"")'
        assert edited["NewSheet"]["A1"].value == "created"
        assert edited["Summary"]["A1"].fill.fgColor.rgb == "00FFFF00"
        assert edited["Summary"]["A1"].font.bold is True
        assert format_result[0]["changed_count"] == 8
    finally:
        edited.close()


def test_hwpx_edit_operations_change_zip_xml(tmp_path) -> None:
    path = tmp_path / "proposal.hwpx"
    _write_hwpx(path, "<hp:body><hp:p>OLD</hp:p></hp:body>")

    apply_hwpx_edit(
        path=path,
        operation="replace_text",
        slots={"OLD_TEXT": "OLD", "NEW_TEXT": "NEW"},
        source_filename="proposal.hwpx",
    )
    apply_hwpx_edit(
        path=path,
        operation="add_paragraph",
        slots={"TEXT": "added text"},
        source_filename="proposal.hwpx",
    )

    with zipfile.ZipFile(path) as package:
        xml = package.read("Contents/section0.xml").decode("utf-8")
    assert "NEW" in xml
    assert "added text" in xml


def test_xlsx_edit_workflow_registers_output_and_hides_internal_paths(
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
                "sheets": [{"sheet_name": "Summary"}],
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
        slot_filler=lambda _operation, _instruction: "SHEET=summary; CELL=A1; VALUE=new",
    )

    result = graph.invoke({"file_ref": "file_001", "instruction": "edit"})
    payload = json.loads(result["result"])

    assert payload["edited_file"]["file_id"] == "file_002"
    assert payload["edited_file"]["download_url"].startswith("/api/fs/outputs/")
    assert ".registry" not in result["result"]
    assert ".converted" not in result["result"]
    assert ".outputs" not in result["result"]
    assert (workspace.files_dir / "book_edited.xlsx").is_file()
    assert (workspace.converted_dir / "file_002" / "manifest.json").is_file()


def _write_hwpx(path: Path, xml: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("Contents/section0.xml", xml)
