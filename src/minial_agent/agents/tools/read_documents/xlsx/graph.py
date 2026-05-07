import json

from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.utils.activity import emit_read_step
from minial_agent.agents.tools.read_documents.xlsx.nodes import inspect_workbook, read_question_range, resolve_xlsx_artifact
from minial_agent.agents.tools.read_documents.xlsx.state import XlsxReadState


def build_xlsx_read_workflow(
    workspace: UploadWorkspace,
):
    graph = StateGraph(XlsxReadState)
    graph.add_node(
        "resolve_xlsx_artifact",
        lambda state: _resolve_xlsx_artifact(state, workspace=workspace),
    )
    graph.add_node(
        "inspect_workbook",
        _inspect_workbook,
    )
    graph.add_node(
        "read_question_range",
        _read_question_range,
    )
    graph.add_node("build_xlsx_answer", _build_xlsx_answer)
    graph.add_edge(START, "resolve_xlsx_artifact")
    graph.add_edge("resolve_xlsx_artifact", "inspect_workbook")
    graph.add_edge("inspect_workbook", "read_question_range")
    graph.add_edge("read_question_range", "build_xlsx_answer")
    graph.add_edge("build_xlsx_answer", END)
    return graph.compile()


def _resolve_xlsx_artifact(
    state: XlsxReadState,
    *,
    workspace: UploadWorkspace,
) -> XlsxReadState:
    emit_read_step(
        file_type="xlsx",
        step="resolve",
        message="XLSX 파일을 확인합니다.",
        summary={"path": state["file_ref"]},
    )
    artifact = resolve_xlsx_artifact(workspace, state["file_ref"])
    emit_read_step(
        file_type="xlsx",
        step="resolve",
        message="XLSX 파일 확인을 완료했습니다.",
        status="completed",
        summary={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def _inspect_workbook(state: XlsxReadState) -> XlsxReadState:
    emit_read_step(
        file_type="xlsx",
        step="workbook",
        message="XLSX 시트 구성을 확인합니다.",
        summary={"path": state["artifact"].visible_name},
    )
    workbook = inspect_workbook(state["artifact"])
    emit_read_step(
        file_type="xlsx",
        step="workbook",
        message=f"XLSX 시트 {workbook.get('sheet_count', 0)}개를 확인했습니다.",
        status="completed",
        summary={"path": state["artifact"].visible_name, "result": f"{workbook.get('sheet_count', 0)} sheets"},
    )
    return {"workbook": workbook}


def _read_question_range(state: XlsxReadState) -> XlsxReadState:
    emit_read_step(
        file_type="xlsx",
        step="range",
        message="질문에 명시된 XLSX 범위를 확인합니다.",
    )
    selected_range = read_question_range(
        state["artifact"],
        question=state.get("question", ""),
        workbook=state.get("workbook", {}),
    )
    emit_read_step(
        file_type="xlsx",
        step="range",
        message="XLSX 범위 확인을 완료했습니다.",
        status="completed",
        summary={"result": "range loaded" if selected_range else "no explicit range"},
    )
    return {"selected_range": selected_range}


def _build_xlsx_answer(state: XlsxReadState) -> XlsxReadState:
    emit_read_step(
        file_type="xlsx",
        step="answer",
        message="XLSX 근거를 정리해 답변을 준비합니다.",
    )
    result = {
        "file_id": state["artifact"].file_id,
        "filename": state["artifact"].visible_name,
        "question": state.get("question", ""),
        "workbook": state.get("workbook", {}),
        "selected_range": state.get("selected_range", {}),
        "guidance": (
            "Use the XLSX editor subagent session tools for calculations, dataframe "
            "transforms, workbook edits, formulas, or export tasks."
        ),
    }
    emit_read_step(
        file_type="xlsx",
        step="answer",
        message="XLSX 답변 근거 정리를 완료했습니다.",
        status="completed",
        summary={"result": f"{len(result.get('workbook', {}).get('sheets', []))} sheets"},
    )
    return {
        "answer_payload": result,
        "result": json.dumps(result, ensure_ascii=False),
    }
