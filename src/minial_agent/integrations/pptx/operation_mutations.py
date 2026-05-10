from typing import Any

from pptx.enum.shapes import MSO_SHAPE

from minial_agent.integrations.pptx.ingest import ingest_pptx_presentation
from minial_agent.integrations.pptx.model import PptxDeck, PptxElement, PptxOperation
from minial_agent.integrations.pptx.operation_guards import (
    shape_by_element,
    slide_and_element,
    slide_by_id,
)


def apply_operation(
    *,
    presentation: Any,
    deck: PptxDeck,
    operation: PptxOperation,
    origin: str,
) -> str | None:
    if operation.type == "updateText":
        slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
        shape = shape_by_element(presentation, slide.index, element)
        if not getattr(shape, "has_text_frame", False):
            raise ValueError(f"PPTX element is not editable text: {element.id}")
        shape.text = operation.content or ""
        element.content = operation.content or ""
        if element.role == "title":
            slide.title = element.content
        if origin == "user":
            element.manualOverrides.content = True
        return slide.id

    if operation.type == "updateStyle":
        slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
        element.style = operation.style or element.style
        if origin == "user":
            element.manualOverrides.style = True
        return slide.id

    if operation.type == "moveElement":
        slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
        shape = shape_by_element(presentation, slide.index, element)
        shape.left = int(operation.x)
        shape.top = int(operation.y)
        element.x = int(operation.x)
        element.y = int(operation.y)
        if origin == "user":
            element.manualOverrides.position = True
        return slide.id

    if operation.type == "resizeElement":
        slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
        shape = shape_by_element(presentation, slide.index, element)
        shape.width = int(operation.width)
        shape.height = int(operation.height)
        element.width = int(operation.width)
        element.height = int(operation.height)
        if origin == "user":
            element.manualOverrides.size = True
        return slide.id

    if operation.type == "addElement":
        slide = slide_by_id(deck, operation.slideId)
        new_element = add_element_to_presentation(
            presentation,
            slide.index,
            operation.element,
        )
        slide.elements.append(new_element)
        return slide.id

    if operation.type == "deleteElement":
        slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
        shape = shape_by_element(presentation, slide.index, element)
        shape._element.getparent().remove(shape._element)
        slide.elements = [item for item in slide.elements if item.id != element.id]
        return slide.id

    if operation.type == "applyLayout":
        slide = slide_by_id(deck, operation.slideId)
        slide.layoutType = operation.layoutId or slide.layoutType
        return slide.id

    if operation.type == "createSlide":
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        title = (operation.contentMap or {}).get("title", "")
        body = (operation.contentMap or {}).get("subtitle", "")
        if slide.shapes.title is not None:
            slide.shapes.title.text = str(title)
        if len(slide.placeholders) > 1 and body:
            slide.placeholders[1].text = str(body)
        rebuilt = ingest_pptx_deck_from_presentation(
            presentation,
            source_deck=deck,
        )
        deck.slides = rebuilt.slides
        return f"slide-{len(deck.slides)}"

    if operation.type == "deleteSlide":
        slide = slide_by_id(deck, operation.slideId)
        slide_id = presentation.slides._sldIdLst[slide.index - 1].rId
        presentation.part.drop_rel(slide_id)
        del presentation.slides._sldIdLst[slide.index - 1]
        deck.slides = [item for item in deck.slides if item.id != operation.slideId]
        for index, item in enumerate(deck.slides, start=1):
            item.index = index
        return operation.slideId

    if operation.type == "reorderSlides":
        reorder_slides(presentation, operation.slideIdOrder or [])
        order = {
            slide_id: index
            for index, slide_id in enumerate(operation.slideIdOrder or [], start=1)
        }
        deck.slides = sorted(deck.slides, key=lambda slide: order[slide.id])
        for index, slide in enumerate(deck.slides, start=1):
            slide.index = index
        return deck.slides[0].id if deck.slides else None

    raise ValueError(f"Unsupported PPTX operation: {operation.type}")


def add_element_to_presentation(
    presentation: Any,
    slide_index: int,
    element: PptxElement | None,
) -> PptxElement:
    if element is None:
        raise ValueError("addElement requires an element.")
    slide = presentation.slides[slide_index - 1]
    if element.type == "text":
        shape = slide.shapes.add_textbox(
            element.x,
            element.y,
            element.width,
            element.height,
        )
        shape.text = element.content
    elif element.type == "shape":
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            element.x,
            element.y,
            element.width,
            element.height,
        )
    else:
        raise ValueError(f"addElement does not support element type: {element.type}")

    return element.model_copy(
        update={
            "id": f"shape-{shape.shape_id}",
            "pptxShapeId": int(shape.shape_id),
            "manualOverrides": {
                "position": True,
                "size": True,
                "content": element.type == "text",
                "style": False,
            },
        }
    )


def reorder_slides(presentation: Any, slide_id_order: list[str]) -> None:
    expected = [f"slide-{index}" for index in range(1, len(presentation.slides) + 1)]
    if sorted(slide_id_order) != sorted(expected):
        raise ValueError("reorderSlides must include every existing slide exactly once.")
    slide_id_list = presentation.slides._sldIdLst
    items = list(slide_id_list)
    reordered = [items[int(slide_id.removeprefix("slide-")) - 1] for slide_id in slide_id_order]
    for item in list(slide_id_list):
        slide_id_list.remove(item)
    for item in reordered:
        slide_id_list.append(item)


def ingest_pptx_deck_from_presentation(
    presentation: Any,
    *,
    source_deck: PptxDeck,
) -> PptxDeck:
    return ingest_pptx_presentation(
        presentation,
        deck_id=source_deck.id,
        title=source_deck.title,
        revision=source_deck.revision,
    )
