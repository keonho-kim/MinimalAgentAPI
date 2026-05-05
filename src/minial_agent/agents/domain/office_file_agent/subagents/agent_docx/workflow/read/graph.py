import json

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.domain.office_file_agent.subagents.utils.activity import emit_read_step
from minial_agent.agents.domain.office_file_agent.subagents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.agents.domain.office_file_agent.subagents.utils.scan import PageScanner
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.read.nodes import build_docx_answer, resolve_docx_artifact, scan_docx_pages
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.workflow.read.state import DocxReadState


def build_docx_read_workflow(
    workspace: UploadWorkspace,
    *,
    page_scanner: PageScanner | None = None,
):
    graph = StateGraph(DocxReadState)
    graph.add_node(
        "resolve_docx_artifact",
        lambda state: _resolve_docx_artifact(state, workspace=workspace),
    )
    graph.add_node(
        "scan_docx_pages",
        lambda state: _scan_docx_pages(state, page_scanner=page_scanner),
    )
    graph.add_node("build_docx_answer", _build_docx_answer)
    graph.add_edge(START, "resolve_docx_artifact")
    graph.add_edge("resolve_docx_artifact", "scan_docx_pages")
    graph.add_edge("scan_docx_pages", "build_docx_answer")
    graph.add_edge("build_docx_answer", END)
    return graph.compile()


def _resolve_docx_artifact(
    state: DocxReadState,
    *,
    workspace: UploadWorkspace,
) -> DocxReadState:
    emit_read_step(
        file_type="docx",
        step="resolve",
        message="DOCX 파일을 확인합니다.",
        summary={"path": state["file_ref"]},
    )
    artifact = resolve_docx_artifact(workspace, state["file_ref"])
    emit_read_step(
        file_type="docx",
        step="resolve",
        message="DOCX 파일 확인을 완료했습니다.",
        status="completed",
        summary={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def _scan_docx_pages(
    state: DocxReadState,
    *,
    page_scanner: PageScanner | None,
) -> DocxReadState:
    pages = state["artifact"].manifest.get("pages", [])
    page_count = len(pages) if isinstance(pages, list) else 0
    emit_read_step(
        file_type="docx",
        step="scan",
        message=f"DOCX 페이지 {page_count}개를 스캔합니다.",
        summary={"path": state["artifact"].visible_name, "description": f"{page_count} pages"},
    )
    relevant_pages, scanned_pages = scan_docx_pages(
        state["artifact"],
        question=state.get("question", ""),
        page_scanner=page_scanner,
    )
    emit_read_step(
        file_type="docx",
        step="scan",
        message=f"DOCX 페이지 스캔을 완료했습니다. 관련 페이지 {len(relevant_pages)}개를 찾았습니다.",
        status="completed",
        summary={"path": state["artifact"].visible_name, "result": f"{scanned_pages} pages scanned"},
    )
    return {
        "relevant_pages": relevant_pages,
        "scanned_pages": scanned_pages,
    }


def _build_docx_answer(state: DocxReadState) -> DocxReadState:
    emit_read_step(
        file_type="docx",
        step="answer",
        message="DOCX 근거를 정리해 답변을 준비합니다.",
    )
    result = build_docx_answer(
        state.get("relevant_pages", []),
        state.get("scanned_pages", 0),
    )
    emit_read_step(
        file_type="docx",
        step="answer",
        message="DOCX 답변 근거 정리를 완료했습니다.",
        status="completed",
        summary={"result": f"{result.get('relevant_page_count', 0)} relevant pages"},
    )
    return {
        "answer_payload": result,
        "result": json.dumps(result, ensure_ascii=False),
    }


@tool
def answer_docx_question(file_path: str, question: str, runtime: ToolRuntime) -> str:
    """Answer a question about a DOCX file."""
    try:
        workflow = build_docx_read_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke({"file_ref": file_path, "question": question})
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)
