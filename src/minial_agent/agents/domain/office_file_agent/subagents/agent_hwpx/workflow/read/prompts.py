PAGE_SCAN_PROMPT = """Answer with one line only in this format: `<0/1>; <evidence>`.
Return 1 only when the HWPX page contains evidence for the question.
Do not return JSON or markdown.
Do not generate filename or page_number.
Return `0; no_evidence` when the page is not relevant.
Question: {question}
"""
