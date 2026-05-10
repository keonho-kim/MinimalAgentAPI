import json
import shutil
from pathlib import Path

from minial_agent.integrations.pptx.ingest import load_or_ingest_pptx_deck
from minial_agent.integrations.upload.conversion import convert_to_pdf, copy_pdf, render_pdf_pages
from minial_agent.integrations.upload.xlsx import build_xlsx_artifacts


def build_upload_artifacts(
    *,
    source_path: Path,
    file_id: str,
    file_type: str,
    converted_dir: Path,
    cache_dir: Path,
) -> None:
    pdf_path = converted_dir / "source.pdf"
    pages_dir = converted_dir / "pages"
    workbook_index_path = converted_dir / "workbook_index.json"
    sheet_pages_root = converted_dir / "xlsx" / "sheets"

    if file_type == "pdf":
        copy_pdf(source_path, pdf_path)
    else:
        pdf_output_dir = converted_dir / ".pdf"
        convert_to_pdf(source_path, pdf_output_dir, pdf_path)
        shutil.rmtree(pdf_output_dir, ignore_errors=True)

    pages = render_pdf_pages(pdf_path, pages_dir)
    if file_type == "xlsx":
        build_xlsx_artifacts(
            source_path=source_path,
            file_id=file_id,
            converted_dir=converted_dir,
            cache_dir=cache_dir,
        )
    if file_type == "pptx":
        load_or_ingest_pptx_deck(cache_dir=cache_dir, source_path=source_path)

    manifest = {
        "file_id": file_id,
        "source_filename": source_path.name,
        "source_path": str(source_path),
        "file_type": file_type,
        "converted_dir": str(converted_dir),
        "pdf_path": str(pdf_path),
        "pages": [
            {
                "page_number": page.page_number,
                "image_filename": page.image_filename,
                "image_path": page.image_path,
            }
            for page in pages
        ],
        "status": "converted",
    }
    if file_type == "xlsx":
        manifest["workbook_index_path"] = str(workbook_index_path)
        manifest["sheet_pages_root"] = str(sheet_pages_root)
    if file_type == "pptx":
        manifest["deck_store"] = str(cache_dir / "pptx_decks")

    (converted_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
