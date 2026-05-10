import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import fitz

from minial_agent.integrations.upload.models import UploadedPage


class ConversionError(RuntimeError):
    pass


def convert_to_pdf(source_path: Path, output_dir: Path, target_pdf: Path) -> None:
    _convert_with_libreoffice(
        source_path=source_path,
        output_dir=output_dir,
        target_path=target_pdf,
        target_format="pdf",
    )


def convert_to_pptx(source_path: Path, output_dir: Path, target_pptx: Path) -> None:
    _convert_with_libreoffice(
        source_path=source_path,
        output_dir=output_dir,
        target_path=target_pptx,
        target_format="pptx",
    )


def convert_to_office_format(
    source_path: Path,
    output_dir: Path,
    target_path: Path,
    target_format: str,
) -> None:
    _convert_with_libreoffice(
        source_path=source_path,
        output_dir=output_dir,
        target_path=target_path,
        target_format=target_format,
    )


def _convert_with_libreoffice(
    *,
    source_path: Path,
    output_dir: Path,
    target_path: Path,
    target_format: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "soffice",
        "--headless",
        "--convert-to",
        target_format,
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

    generated_path = output_dir / f"{source_path.stem}.{target_format}"
    if not generated_path.exists():
        generated_files = sorted(output_dir.glob(f"*.{target_format}"))
        if len(generated_files) != 1:
            raise ConversionError(f"LibreOffice did not produce a {target_format.upper()} file")
        generated_path = generated_files[0]

    if generated_path != target_path:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            target_path.unlink()
        generated_path.replace(target_path)


def copy_pdf(source_path: Path, target_pdf: Path) -> None:
    target_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_pdf)


def render_pdf_pages(pdf_path: Path, pages_dir: Path) -> list[UploadedPage]:
    try:
        return _render_pdf_pages_once(pdf_path, pages_dir)
    except ConversionError as first_error:
        repaired_path = _repaired_pdf_path(pdf_path)
        try:
            _repair_pdf(source_pdf=pdf_path, repaired_pdf=repaired_path)
            return _render_pdf_pages_once(repaired_path, pages_dir)
        except ConversionError as second_error:
            raise ConversionError(
                "Failed to render PDF pages after repair: "
                f"{first_error}; retry failed: {second_error}"
            ) from second_error
        finally:
            repaired_path.unlink(missing_ok=True)


def _render_pdf_pages_once(pdf_path: Path, pages_dir: Path) -> list[UploadedPage]:
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages: list[UploadedPage] = []

    with _quiet_mupdf_messages():
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
        except Exception as exc:
            raise ConversionError(f"Failed to render PDF page: {exc}") from exc
        finally:
            document.close()

    return pages


def _repair_pdf(*, source_pdf: Path, repaired_pdf: Path) -> None:
    with _quiet_mupdf_messages():
        try:
            document = fitz.open(source_pdf)
        except Exception as exc:
            raise ConversionError(f"Failed to open PDF for repair: {exc}") from exc

        try:
            repaired_pdf.unlink(missing_ok=True)
            document.save(
                repaired_pdf,
                garbage=4,
                clean=True,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
            )
        except Exception as exc:
            raise ConversionError(f"Failed to repair PDF: {exc}") from exc
        finally:
            document.close()


def _repaired_pdf_path(pdf_path: Path) -> Path:
    return pdf_path.with_name(f"{pdf_path.stem}.repaired{pdf_path.suffix}")


@contextmanager
def _quiet_mupdf_messages() -> Iterator[None]:
    show_errors = fitz.TOOLS.mupdf_display_errors()
    show_warnings = fitz.TOOLS.mupdf_display_warnings()
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    try:
        yield
    finally:
        fitz.TOOLS.mupdf_display_errors(show_errors)
        fitz.TOOLS.mupdf_display_warnings(show_warnings)
