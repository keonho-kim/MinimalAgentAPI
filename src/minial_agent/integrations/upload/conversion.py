import shutil
import subprocess
from pathlib import Path

import fitz

from minial_agent.integrations.upload.models import UploadedPage


class ConversionError(RuntimeError):
    pass


def convert_to_pdf(source_path: Path, output_dir: Path, target_pdf: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(source_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise ConversionError(message or "LibreOffice conversion failed")

    generated_pdf = output_dir / f"{source_path.stem}.pdf"
    if not generated_pdf.exists():
        pdfs = sorted(output_dir.glob("*.pdf"))
        if len(pdfs) != 1:
            raise ConversionError("LibreOffice did not produce a PDF")
        generated_pdf = pdfs[0]

    if generated_pdf != target_pdf:
        if target_pdf.exists():
            target_pdf.unlink()
        generated_pdf.replace(target_pdf)


def copy_pdf(source_path: Path, target_pdf: Path) -> None:
    target_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_pdf)


def render_pdf_pages(pdf_path: Path, pages_dir: Path) -> list[UploadedPage]:
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages: list[UploadedPage] = []

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise ConversionError(f"Failed to open PDF: {exc}") from exc

    try:
        for index, page in enumerate(document, start=1):
            image_filename = f"page_{index:03d}.png"
            image_path = pages_dir / image_filename
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pixmap.save(image_path)
            pages.append(
                UploadedPage(
                    page_number=index,
                    image_filename=image_filename,
                    image_path=str(image_path),
                )
            )
    finally:
        document.close()

    return pages
