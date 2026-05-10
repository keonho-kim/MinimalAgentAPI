import json
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from minial_agent.integrations.upload.conversion import convert_to_pdf, render_pdf_pages
from minial_agent.integrations.upload.xlsx_metadata import SPREADSHEET_NS, inspect_workbook


def build_xlsx_artifacts(
    *,
    source_path: Path,
    file_id: str,
    converted_dir: Path,
    cache_dir: Path,
) -> None:
    sheets = inspect_workbook(source_path)
    xlsx_dir = converted_dir / "xlsx"
    sheets_dir = xlsx_dir / "sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    workbook_entries = []
    for index, sheet in enumerate(sheets):
        sheet_id = f"sheet_{index + 1:04d}"
        sheet_dir = sheets_dir / sheet_id
        sheet_dir.mkdir(parents=True, exist_ok=True)
        sheet_summary_path = sheet_dir / "sheet.json"
        sheet_entry = {
            "sheet_id": sheet_id,
            "sheet_name": sheet["sheet_name"],
            "index": index,
            "visible": sheet["visible"],
            "used_range": sheet["used_range"],
            "has_formulas": sheet["has_formulas"],
            "formula_count": sheet["formula_count"],
            "has_tables": sheet.get("has_tables", False),
            "has_charts": sheet.get("has_charts", False),
            "sheet_summary_path": str(sheet_summary_path),
        }

        sheet_summary = dict(sheet_entry)
        sheet_summary["headers"] = sheet.get("headers", [])
        sheet_summary["sample_rows"] = sheet.get("sample_rows", [])
        sheet_summary["formula_summary"] = sheet.get("formula_summary", "")
        sheet_summary["chart_summary"] = sheet.get("chart_summary", "")
        sheet_summary["text_summary"] = sheet.get("text_summary", "")
        try:
            pages = render_single_sheet(
                source_path=source_path,
                sheet_index=index,
                sheet_dir=sheet_dir,
                cache_dir=cache_dir,
            )
            sheet_summary["pages"] = [
                {
                    "page_number": page.page_number,
                    "image_filename": page.image_filename,
                    "image_path": page.image_path,
                }
                for page in pages
            ]
        except Exception as exc:
            sheet_summary["conversion_error"] = str(exc)

        sheet_summary_path.write_text(
            json.dumps(sheet_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        workbook_entries.append(sheet_entry)

    workbook_index = {
        "file_id": file_id,
        "source_filename": source_path.name,
        "sheet_count": len(workbook_entries),
        "sheets": workbook_entries,
    }
    (converted_dir / "workbook_index.json").write_text(
        json.dumps(workbook_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_single_sheet(
    *,
    source_path: Path,
    sheet_index: int,
    sheet_dir: Path,
    cache_dir: Path,
):
    pages_dir = sheet_dir / "pages"
    with tempfile.TemporaryDirectory(dir=cache_dir) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        single_sheet_path = temp_dir / source_path.name
        copy_with_only_sheet_visible(source_path, single_sheet_path, sheet_index)
        pdf_dir = temp_dir / "pdf"
        pdf_path = temp_dir / "source.pdf"
        convert_to_pdf(single_sheet_path, pdf_dir, pdf_path)
        return render_pdf_pages(pdf_path, pages_dir)


def copy_with_only_sheet_visible(
    source_path: Path,
    target_path: Path,
    visible_sheet_index: int,
) -> None:
    with zipfile.ZipFile(source_path) as source:
        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "xl/workbook.xml":
                    data = set_visible_sheet(data, visible_sheet_index)
                target.writestr(item, data)


def set_visible_sheet(workbook_xml: bytes, visible_sheet_index: int) -> bytes:
    root = ElementTree.fromstring(workbook_xml)
    sheets = root.findall(f".//{{{SPREADSHEET_NS}}}sheet")
    for index, sheet in enumerate(sheets):
        if index == visible_sheet_index:
            sheet.attrib.pop("state", None)
        else:
            sheet.attrib["state"] = "hidden"
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)
