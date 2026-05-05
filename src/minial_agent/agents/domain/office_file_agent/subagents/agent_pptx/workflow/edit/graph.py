import json
from pathlib import Path

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.tool_node import ToolRuntime

from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.storage import unique_path

from minial_agent.agents.domain.office_file_agent.subagents.utils.activity import emit_edit_step
from minial_agent.agents.domain.office_file_agent.subagents.utils.edit_protocol import OperationSelector, SlotFiller
from minial_agent.agents.domain.office_file_agent.subagents.utils.runtime import sanitize_tool_error, workspace_from_tool_runtime
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.workflow.edit.nodes import apply_pptx_edit_spec, build_pptx_edit_spec, register_pptx_edit_result, resolve_pptx_artifact
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.workflow.edit.state import PptxEditState


def build_pptx_edit_workflow(
    workspace: UploadWorkspace,
    *,
    operation_selector: OperationSelector | None = None,
    slot_filler: SlotFiller | None = None,
):
    graph = StateGraph(PptxEditState)
    graph.add_node(
        "resolve_pptx_artifact",
        lambda state: _resolve_pptx_artifact(state, workspace=workspace),
    )
    graph.add_node(
        "build_pptx_edit_spec",
        lambda state: _build_pptx_edit_spec(
            state,
            operation_selector=operation_selector,
            slot_filler=slot_filler,
        ),
    )
    graph.add_node(
        "apply_pptx_edit_spec",
        lambda state: _apply_pptx_edit_spec(state, workspace=workspace),
    )
    graph.add_node(
        "register_pptx_edit_result",
        lambda state: _register_pptx_edit_result(state, workspace=workspace),
    )
    graph.add_edge(START, "resolve_pptx_artifact")
    graph.add_edge("resolve_pptx_artifact", "build_pptx_edit_spec")
    graph.add_edge("build_pptx_edit_spec", "apply_pptx_edit_spec")
    graph.add_edge("apply_pptx_edit_spec", "register_pptx_edit_result")
    graph.add_edge("register_pptx_edit_result", END)
    return graph.compile()


def _resolve_pptx_artifact(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="resolve",
        message="수정할 PPTX 파일을 확인합니다.",
        summary={"path": state["file_ref"]},
    )
    artifact = resolve_pptx_artifact(workspace, state["file_ref"])
    emit_edit_step(
        file_type="pptx",
        step="resolve",
        message="PPTX 파일 확인을 완료했습니다.",
        status="completed",
        summary={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def _build_pptx_edit_spec(
    state: PptxEditState,
    *,
    operation_selector: OperationSelector | None,
    slot_filler: SlotFiller | None,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="spec",
        message="PPTX 수정 방법을 정리합니다.",
        summary={"path": state["artifact"].visible_name},
    )
    edit_spec = build_pptx_edit_spec(
        instruction=state.get("instruction", ""),
        operation_selector=operation_selector,
        slot_filler=slot_filler,
    )
    emit_edit_step(
        file_type="pptx",
        step="spec",
        message=f"PPTX 수정 작업을 {edit_spec['operation']} 방식으로 준비했습니다.",
        status="completed",
        summary={"path": state["artifact"].visible_name, "description": str(edit_spec["operation"])},
    )
    return {"edit_spec": edit_spec}


def _apply_pptx_edit_spec(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="apply",
        message="PPTX 수정 내용을 파일에 적용합니다.",
        summary={"path": state["artifact"].visible_name},
    )
    edited_path = _edited_path(
        workspace=workspace,
        visible_name=state["artifact"].visible_name,
        suffix=".pptx",
    )
    changed_items = apply_pptx_edit_spec(
        artifact=state["artifact"],
        edit_spec=state["edit_spec"],
        edited_path=edited_path,
    )
    emit_edit_step(
        file_type="pptx",
        step="apply",
        message=f"PPTX 수정 적용을 완료했습니다. 변경 항목 {len(changed_items)}개를 만들었습니다.",
        status="completed",
        summary={"path": state["artifact"].visible_name, "result": f"{len(changed_items)} changes"},
    )
    return {
        "edited_path": edited_path,
        "changed_items": changed_items,
    }


def _register_pptx_edit_result(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="register",
        message="PPTX 수정본을 등록하고 다운로드 정보를 준비합니다.",
        summary={"path": state["artifact"].visible_name},
    )
    result = register_pptx_edit_result(
        workspace=workspace,
        artifact=state["artifact"],
        edited_path=state["edited_path"],
        changed_items=state.get("changed_items", []),
    )
    _cleanup_edited_path(state["edited_path"])
    emit_edit_step(
        file_type="pptx",
        step="register",
        message="PPTX 수정본 등록을 완료했습니다.",
        status="completed",
        summary={"path": result.get("edited_file", {}).get("filename"), "result": result.get("edited_file", {}).get("download_url")},
    )
    return {
        "result_payload": result,
        "result": json.dumps(result, ensure_ascii=False),
    }


def _edited_path(
    *,
    workspace: UploadWorkspace,
    visible_name: str,
    suffix: str,
) -> Path:
    edits_dir = workspace.cache_dir / "edits"
    edits_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(edits_dir / f"{Path(visible_name).stem}_edited{suffix}")


def _cleanup_edited_path(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


@tool
def edit_pptx(file_path: str, instruction: str, runtime: ToolRuntime) -> str:
    """Edit a PPTX file."""
    try:
        workflow = build_pptx_edit_workflow(workspace_from_tool_runtime(runtime))
        result = workflow.invoke({"file_ref": file_path, "instruction": instruction})
        return result["result"]
    except Exception as exc:
        return sanitize_tool_error(exc)
