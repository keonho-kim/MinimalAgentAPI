from textwrap import dedent
from langchain_core.prompts import PromptTemplate


_PAGE_SCAN_PROMPT = dedent(
    """Answer with one line only in this format: `<0/1>; <evidence>`.
Return 1 only when the PPTX page contains evidence for the question.
Do not return JSON or markdown.
Do not generate filename or page_number.
Return `0; no_evidence` when the page is not relevant.
Question: {question}
""".strip()
)

PAGE_SCAN_PROMPT = PromptTemplate.from_template(_PAGE_SCAN_PROMPT)