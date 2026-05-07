from minial_agent.agents.tools.base_tools import BASE_TOOLS
from minial_agent.agents.tools.fs import FS_TOOLS
from minial_agent.agents.tools.read_documents import (
    read_docx_file as _read_docx_file,
    read_hwpx_file as _read_hwpx_file,
    read_pdf_file as _read_pdf_file,
    read_pptx_file as _read_pptx_file,
    read_xlsx_file as _read_xlsx_file,
)


OFFICE_READ_TOOLS = [
    _read_pdf_file,
    _read_docx_file,
    _read_hwpx_file,
    _read_pptx_file,
    _read_xlsx_file,
]

ALL_AGENT_TOOLS = [
    *BASE_TOOLS,
    *FS_TOOLS,
    *OFFICE_READ_TOOLS,
]

__all__ = [
    "ALL_AGENT_TOOLS",
    "BASE_TOOLS",
    "FS_TOOLS",
    "OFFICE_READ_TOOLS",
]
