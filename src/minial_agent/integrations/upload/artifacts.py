import json
import shutil
from pathlib import Path

from .conversion import convert_to_pdf, copy_pdf, render_pdf_pages
from .xlsx import build_xlsx_artifacts


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

    if file_type == "pdf":
        copy_pdf(source_path, pdf_path)
    else:
        pdf_output_dir = converted_dir / ".pdf"
        convert_to_pdf(source_path, pdf_output_dir, pdf_path)
        shutil.rmtree(pdf_output_dir, ignore_errors=True)

    pages = render_pdf_pages(pdf_path, pages_dir)
    manifest = {
        "file_id": file_id,
        "source_filename": source_path.name,
        "source_path": str(source_path),
        "file_type": file_type,
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
    (converted_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if file_type == "xlsx":
        build_xlsx_artifacts(
            source_path=source_path,
            file_id=file_id,
            converted_dir=converted_dir,
            cache_dir=cache_dir,
        )
