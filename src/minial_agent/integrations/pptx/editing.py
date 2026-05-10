import shutil
from pathlib import Path

from pptx import Presentation

from minial_agent.integrations.upload.artifacts import build_upload_artifacts
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.registry import UploadRegistry


def update_pptx_text_shape(
    *,
    workspace: UploadWorkspace,
    source_path: Path,
    slide_number: int,
    shape_id: int,
    text: str | None,
    bounds: dict[str, int] | None,
) -> None:
    presentation = Presentation(source_path)
    if slide_number < 1 or slide_number > len(presentation.slides):
        raise ValueError(f"PPTX slide is out of range: {slide_number}")

    slide = presentation.slides[slide_number - 1]
    for shape in slide.shapes:
        if int(getattr(shape, "shape_id", 0)) != shape_id:
            continue
        if not getattr(shape, "has_text_frame", False):
            raise ValueError(f"PPTX shape is not editable text: {shape_id}")
        if text is not None:
            shape.text = text
        if bounds is not None:
            shape.left = int(bounds["left"])
            shape.top = int(bounds["top"])
            shape.width = int(bounds["width"])
            shape.height = int(bounds["height"])
        presentation.save(source_path)
        _refresh_upload_artifacts(workspace=workspace, source_path=source_path)
        return

    raise ValueError(f"PPTX text block was not found: {shape_id}")


def _refresh_upload_artifacts(
    *,
    workspace: UploadWorkspace,
    source_path: Path,
) -> None:
    registry = UploadRegistry(workspace.registry_path)
    entry = registry.lookup(visible_path=str(source_path))
    if not entry or entry.get("file_type") != "pptx":
        return

    file_id = str(entry.get("file_id", ""))
    converted_dir_value = entry.get("converted_dir")
    if not file_id or not isinstance(converted_dir_value, str):
        return

    converted_dir = Path(converted_dir_value)
    temp_dir = converted_dir.with_name(f"{converted_dir.name}.tmp")
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        build_upload_artifacts(
            source_path=source_path,
            file_id=file_id,
            file_type="pptx",
            converted_dir=temp_dir,
            cache_dir=workspace.cache_dir,
        )
        shutil.rmtree(converted_dir, ignore_errors=True)
        temp_dir.replace(converted_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    registry.update_status(file_id, status="converted")
