from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from minial_agent.integrations.pptx.model import (
    PptxCanvas,
    PptxDeck,
    PptxElement,
    PptxElementStyle,
    PptxManualOverrides,
    PptxSlide,
)
from minial_agent.integrations.pptx.store import PptxDeckStore, pptx_db_path


def load_or_ingest_pptx_deck(*, cache_dir: Path, source_path: Path) -> PptxDeck:
    store = PptxDeckStore(pptx_db_path(cache_dir, source_path))
    deck, source_stat = store.load()
    current_stat = _source_stat(source_path)
    if deck is not None and source_stat == current_stat:
        return deck

    previous_revision = deck.revision if deck else 0
    deck = ingest_pptx_deck(source_path, revision=previous_revision)
    store.save(deck, source_stat=current_stat)
    return deck


def save_pptx_deck(*, cache_dir: Path, source_path: Path, deck: PptxDeck) -> None:
    PptxDeckStore(pptx_db_path(cache_dir, source_path)).save(
        deck,
        source_stat=_source_stat(source_path),
    )


def ingest_pptx_deck(source_path: Path, *, revision: int = 0) -> PptxDeck:
    presentation = Presentation(source_path)
    return ingest_pptx_presentation(
        presentation,
        deck_id=_deck_id(source_path),
        title=source_path.stem,
        revision=revision,
    )


def ingest_pptx_presentation(
    presentation: Any,
    *,
    deck_id: str,
    title: str,
    revision: int,
) -> PptxDeck:
    slides = [
        _slide_model(slide, deck_id=deck_id, slide_index=index)
        for index, slide in enumerate(presentation.slides, start=1)
    ]
    return PptxDeck(
        id=deck_id,
        title=title,
        sourceType="pptx",
        revision=revision,
        canvas=PptxCanvas(
            width=int(presentation.slide_width),
            height=int(presentation.slide_height),
        ),
        slides=slides,
    )


def _slide_model(slide: Any, *, deck_id: str, slide_index: int) -> PptxSlide:
    slide_id = f"slide-{slide_index}"
    elements = [
        element
        for z_index, shape in enumerate(slide.shapes)
        if (element := _element_model(shape, slide_id=slide_id, z_index=z_index)) is not None
    ]
    title = _slide_title(slide)
    content_hash = _hash([title, _notes_text(slide), *[element.content for element in elements]])
    layout_hash = _hash(
        [
            f"{element.id}:{element.x}:{element.y}:{element.width}:{element.height}:{element.zIndex}"
            for element in elements
        ]
    )
    return PptxSlide(
        id=slide_id,
        deckId=deck_id,
        index=slide_index,
        title=title,
        layoutType=_layout_type(slide),
        elements=elements,
        notes=_notes_text(slide),
        source={"type": "pptx", "originalSlidePath": f"ppt/slides/slide{slide_index}.xml"},
        contentHash=content_hash,
        layoutHash=layout_hash,
        visualHash=layout_hash,
        summaryHash=content_hash,
    )


def _element_model(shape: Any, *, slide_id: str, z_index: int) -> PptxElement | None:
    width = int(getattr(shape, "width", 0))
    height = int(getattr(shape, "height", 0))
    if width <= 0 or height <= 0:
        return None

    shape_id = int(getattr(shape, "shape_id", z_index + 1))
    element_type = _element_type(shape)
    text = str(getattr(shape, "text", "")).strip() if getattr(shape, "has_text_frame", False) else ""
    if element_type == "text" and not text:
        element_type = "shape"
    return PptxElement(
        id=f"shape-{shape_id}",
        slideId=slide_id,
        type=element_type,
        role=_element_role(shape),
        content=text,
        x=int(getattr(shape, "left", 0)),
        y=int(getattr(shape, "top", 0)),
        width=width,
        height=height,
        rotation=float(getattr(shape, "rotation", 0) or 0),
        zIndex=z_index,
        pptxShapeId=shape_id,
        style=_text_style(shape),
        manualOverrides=PptxManualOverrides(),
    )


def _element_type(shape: Any) -> str:
    if getattr(shape, "has_text_frame", False):
        return "text"
    if getattr(shape, "has_table", False):
        return "table"
    if getattr(shape, "has_chart", False):
        return "chart"
    shape_type = getattr(shape, "shape_type", None)
    if shape_type == MSO_SHAPE_TYPE.PICTURE:
        return "image"
    if shape_type == MSO_SHAPE_TYPE.LINE:
        return "line"
    if shape_type == MSO_SHAPE_TYPE.GROUP:
        return "group"
    return "shape"


def _element_role(shape: Any) -> str:
    if not getattr(shape, "is_placeholder", False):
        return "body"
    try:
        placeholder = str(shape.placeholder_format.type).lower()
    except (AttributeError, ValueError):
        return "body"
    if "title" in placeholder:
        return "title"
    if "subtitle" in placeholder:
        return "subtitle"
    return "body"


def _text_style(shape: Any) -> PptxElementStyle:
    if not getattr(shape, "has_text_frame", False):
        return PptxElementStyle()
    paragraphs = shape.text_frame.paragraphs
    if not paragraphs or not paragraphs[0].runs:
        return PptxElementStyle()
    run = paragraphs[0].runs[0]
    font = run.font
    return PptxElementStyle(
        fontFamily=font.name,
        fontSize=float(font.size) if font.size else None,
        fontWeight=700 if font.bold else None,
        color=_font_color(font),
    )


def _font_color(font: Any) -> str | None:
    try:
        rgb = font.color.rgb
    except (AttributeError, ValueError):
        return None
    return f"#{rgb}" if rgb else None


def _slide_title(slide: Any) -> str:
    title_shape = getattr(slide.shapes, "title", None)
    if title_shape is None:
        return ""
    return str(getattr(title_shape, "text", "")).strip()


def _notes_text(slide: Any) -> str:
    if not getattr(slide, "has_notes_slide", False):
        return ""
    notes = []
    for paragraph in slide.notes_slide.notes_text_frame.paragraphs:
        text = paragraph.text.strip()
        if text:
            notes.append(text)
    return "\n".join(notes)


def _layout_type(slide: Any) -> str:
    try:
        return str(slide.slide_layout.name or "unknown")
    except AttributeError:
        return "unknown"


def _deck_id(source_path: Path) -> str:
    return f"deck-{hashlib.sha256(str(source_path.resolve()).encode('utf-8')).hexdigest()[:12]}"


def _source_stat(source_path: Path) -> dict[str, int | str]:
    stat = source_path.stat()
    return {
        "path": str(source_path.resolve()),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def _hash(values: list[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()[:16]
