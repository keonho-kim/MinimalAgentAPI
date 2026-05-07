OPERATION_PROMPT = """Choose exactly one XLSX edit operation for this request.
Allowed operations: write_values, write_formulas, add_sheet, format_range.
Return only the operation name.
Do not return JSON or markdown.
Request: {instruction}
"""

SLOT_PROMPT = """Fill slots for XLSX operation `{operation}`.
Return one line only as KEY=VALUE pairs separated by semicolons.
Do not return JSON or markdown.
Request: {instruction}
"""
