from langgraph.graph import END, START, StateGraph

from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.nodes import (
    apply_pptx_edit_spec_node,
    build_pptx_edit_spec_node,
    register_pptx_edit_result_node,
    resolve_pptx_artifact_node,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.state import (
    PptxEditState,
)
from minial_agent.integrations.upload.models import UploadWorkspace


def build_pptx_edit_workflow(
    workspace: UploadWorkspace,
    *,
    operation_generator=None,
):
    graph = StateGraph(PptxEditState)
    graph.add_node(
        "resolve_pptx_artifact",
        lambda state: resolve_pptx_artifact_node(state, workspace=workspace),
    )
    graph.add_node(
        "build_pptx_edit_spec",
        lambda state: build_pptx_edit_spec_node(
            state,
            workspace=workspace,
            operation_generator=operation_generator,
        ),
    )
    graph.add_node(
        "apply_pptx_edit_spec",
        lambda state: apply_pptx_edit_spec_node(state, workspace=workspace),
    )
    graph.add_node(
        "register_pptx_edit_result",
        lambda state: register_pptx_edit_result_node(state, workspace=workspace),
    )
    graph.add_edge(START, "resolve_pptx_artifact")
    graph.add_edge("resolve_pptx_artifact", "build_pptx_edit_spec")
    graph.add_edge("build_pptx_edit_spec", "apply_pptx_edit_spec")
    graph.add_edge("apply_pptx_edit_spec", "register_pptx_edit_result")
    graph.add_edge("register_pptx_edit_result", END)
    return graph.compile()
