from langgraph.graph import END, START, StateGraph

from minial_agent.integrations.upload.models import UploadWorkspace

from minial_agent.agents.domain.office_file_editor.utils.edit_protocol import OperationSelector, SlotFiller
from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.workflow.edit.nodes import (
    apply_hwpx_edit_spec_node,
    build_hwpx_edit_spec_node,
    register_hwpx_edit_result_node,
    resolve_hwpx_artifact_node,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.workflow.edit.state import HwpxEditState


def build_hwpx_edit_workflow(
    workspace: UploadWorkspace,
    *,
    operation_selector: OperationSelector | None = None,
    slot_filler: SlotFiller | None = None,
):
    graph = StateGraph(HwpxEditState)
    graph.add_node(
        "resolve_hwpx_artifact",
        lambda state: resolve_hwpx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "build_hwpx_edit_spec",
        lambda state: build_hwpx_edit_spec_node(
            state,
            operation_selector=operation_selector,
            slot_filler=slot_filler,
        ),
    )
    graph.add_node(
        "apply_hwpx_edit_spec",
        lambda state: apply_hwpx_edit_spec_node(state, workspace=workspace),
    )
    graph.add_node(
        "register_hwpx_edit_result",
        lambda state: register_hwpx_edit_result_node(state, workspace=workspace),
    )
    graph.add_edge(START, "resolve_hwpx_artifact")
    graph.add_edge("resolve_hwpx_artifact", "build_hwpx_edit_spec")
    graph.add_edge("build_hwpx_edit_spec", "apply_hwpx_edit_spec")
    graph.add_edge("apply_hwpx_edit_spec", "register_hwpx_edit_result")
    graph.add_edge("register_hwpx_edit_result", END)
    return graph.compile()
