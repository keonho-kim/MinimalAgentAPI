from textwrap import dedent
from langchain_core.prompts import PromptTemplate


_PAGE_SCAN_PROMPT = dedent(
    """Return only the answer from this HWPX page when it contains evidence for the question.
Return exactly `None` when this page does not contain evidence.
Do not return `1;`, `0;`, JSON, markdown, filename, page number, or explanation.
Question: {question}
""".strip()
)

PAGE_SCAN_PROMPT = PromptTemplate.from_template(_PAGE_SCAN_PROMPT)
