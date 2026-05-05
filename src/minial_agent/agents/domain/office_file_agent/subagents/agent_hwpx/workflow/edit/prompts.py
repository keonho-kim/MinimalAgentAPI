OPERATION_PROMPT = """Choose exactly one HWPX edit operation for this request.
Allowed operations: replace_text, add_paragraph.
Return only the operation name.
Do not return JSON or markdown.
Request: {instruction}
"""

SLOT_PROMPT = """Fill slots for HWPX operation `{operation}`.
Return one line only as KEY=VALUE pairs separated by semicolons.
Do not return JSON or markdown.
Request: {instruction}
"""
