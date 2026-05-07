OPERATION_PROMPT = """Choose exactly one PPTX edit operation for this request.
Allowed operations: replace_slide_title, replace_slide_text, add_slide.
Return only the operation name.
Do not return JSON or markdown.
Request: {instruction}
"""

SLOT_PROMPT = """Fill slots for PPTX operation `{operation}`.
Return one line only as KEY=VALUE pairs separated by semicolons.
Do not return JSON or markdown.
Request: {instruction}
"""
