OPERATION_PROMPT = """Generate PPTX edit operations for the request.
Return only a JSON array. Do not return markdown.
Allowed operation types:
updateText, updateStyle, addElement, deleteElement, moveElement, resizeElement, applyLayout, reorderSlides, createSlide, deleteSlide.
Use only slideId and elementId values that exist in the deck summary.
Respect manualOverrides. Do not target a user-overridden field.

Deck summary:
{deck_summary}

Request:
{instruction}
"""
