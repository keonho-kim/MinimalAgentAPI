from minial_agent.integrations.pptx.model import PptxDeck, PptxElement, PptxOperation


def manual_override_violation(
    deck: PptxDeck,
    operation: PptxOperation,
    *,
    origin: str,
) -> str | None:
    if origin != "ai" or operation.type in {"addElement", "createSlide"}:
        return None
    try:
        _slide, element = slide_and_element(deck, operation.slideId, operation.elementId)
    except ValueError:
        return None

    if operation.type == "updateText" and element.manualOverrides.content:
        return f"AI operation would overwrite user-edited content: {element.id}"
    if operation.type == "updateStyle" and element.manualOverrides.style:
        return f"AI operation would overwrite user-edited style: {element.id}"
    if operation.type == "moveElement" and element.manualOverrides.position:
        return f"AI operation would move user-positioned element: {element.id}"
    if operation.type == "resizeElement" and element.manualOverrides.size:
        return f"AI operation would resize user-sized element: {element.id}"
    if operation.type == "deleteElement" and (
        element.manualOverrides.content
        or element.manualOverrides.position
        or element.manualOverrides.size
        or element.manualOverrides.style
    ):
        return f"AI operation would delete user-edited element: {element.id}"
    return None


def slide_and_element(
    deck: PptxDeck,
    slide_id: str | None,
    element_id: str | None,
):
    slide = slide_by_id(deck, slide_id)
    for element in slide.elements:
        if element.id == element_id:
            return slide, element
    raise ValueError(f"PPTX element not found: {element_id}")


def slide_by_id(deck: PptxDeck, slide_id: str | None):
    for slide in deck.slides:
        if slide.id == slide_id:
            return slide
    raise ValueError(f"PPTX slide not found: {slide_id}")


def shape_by_element(presentation, slide_index: int, element: PptxElement):
    if element.pptxShapeId is None:
        raise ValueError(f"PPTX element has no source shape: {element.id}")
    slide = presentation.slides[slide_index - 1]
    for shape in slide.shapes:
        if int(getattr(shape, "shape_id", 0)) == element.pptxShapeId:
            return shape
    raise ValueError(f"PPTX shape not found: {element.id}")
