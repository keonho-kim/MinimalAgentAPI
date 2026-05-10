from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.domain.office_file_editor.utils.edit_protocol import OperationSelector, SlotFiller
from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.workflow.edit.nodes import (
    apply_docx_edit_spec_node,
    build_docx_edit_spec_node,
    register_docx_edit_result_node,
    resolve_docx_artifact_node,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.workflow.edit.state import DocxEditState


def build_docx_edit_workflow(
    workspace: UploadWorkspace,
    *,
    operation_selector: OperationSelector | None = None,
    slot_filler: SlotFiller | None = None,
):
    graph = StateGraph(DocxEditState)
    graph.add_node(
        "resolve_docx_artifact",
        lambda state: resolve_docx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "build_docx_edit_spec",
        lambda state: build_docx_edit_spec_node(
            state,
            operation_selector=operation_selector,
            slot_filler=slot_filler,
        ),
    )
    graph.add_node(
        "apply_docx_edit_spec",
        lambda state: apply_docx_edit_spec_node(state, workspace=workspace),
    )
    graph.add_node(
        "register_docx_edit_result",
        lambda state: register_docx_edit_result_node(state, workspace=workspace),
    )
    graph.add_edge(START, "resolve_docx_artifact")
    graph.add_edge("resolve_docx_artifact", "build_docx_edit_spec")
    graph.add_edge("build_docx_edit_spec", "apply_docx_edit_spec")
    graph.add_edge("apply_docx_edit_spec", "register_docx_edit_result")
    graph.add_edge("register_docx_edit_result", END)
    return graph.compile()
