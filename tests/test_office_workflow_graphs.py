from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.workflow.edit import (
    build_docx_edit_workflow,
)
from minial_agent.agents.tools.read_documents.docx import (
    build_docx_read_workflow,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.workflow.edit import (
    build_hwpx_edit_workflow,
)
from minial_agent.agents.tools.read_documents.hwpx import (
    build_hwpx_read_workflow,
)
from minial_agent.agents.tools.read_documents.pdf import (
    build_pdf_read_workflow,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit import (
    build_pptx_edit_workflow,
)
from minial_agent.agents.tools.read_documents.pptx import (
    build_pptx_read_workflow,
)
from minial_agent.agents.tools.read_documents.xlsx import (
    build_xlsx_read_workflow,
)
from minial_agent.integrations.upload import ensure_upload_workspace


def test_document_read_workflows_use_observable_step_nodes(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)

    expected = {
        "docx": {
            "resolve_docx_artifact",
            "scan_docx_pages",
            "build_docx_answer",
        },
        "hwpx": {
            "resolve_hwpx_artifact",
            "scan_hwpx_pages",
            "build_hwpx_answer",
        },
        "pptx": {
            "resolve_pptx_artifact",
            "scan_pptx_pages",
            "build_pptx_answer",
        },
        "pdf": {
            "resolve_pdf_artifact",
            "scan_pdf_pages",
            "build_pdf_answer",
        },
    }
    workflows = {
        "docx": build_docx_read_workflow(workspace),
        "hwpx": build_hwpx_read_workflow(workspace),
        "pptx": build_pptx_read_workflow(workspace),
        "pdf": build_pdf_read_workflow(workspace),
    }

    for file_type, workflow in workflows.items():
        nodes = _node_names(workflow)
        assert "read" not in nodes
        assert expected[file_type] <= nodes


def test_xlsx_read_workflow_uses_observable_step_nodes(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    nodes = _node_names(build_xlsx_read_workflow(workspace))

    assert "read" not in nodes
    assert {
        "resolve_xlsx_artifact",
        "inspect_workbook",
        "read_question_range",
        "build_xlsx_answer",
    } <= nodes


def test_edit_workflows_use_observable_step_nodes(tmp_path) -> None:
    workspace = ensure_upload_workspace(tmp_path)
    expected = {
        "docx": {
            "resolve_docx_artifact",
            "build_docx_edit_spec",
            "apply_docx_edit_spec",
            "register_docx_edit_result",
        },
        "hwpx": {
            "resolve_hwpx_artifact",
            "build_hwpx_edit_spec",
            "apply_hwpx_edit_spec",
            "register_hwpx_edit_result",
        },
        "pptx": {
            "resolve_pptx_artifact",
            "build_pptx_edit_spec",
            "apply_pptx_edit_spec",
            "register_pptx_edit_result",
        },
    }
    workflows = {
        "docx": build_docx_edit_workflow(workspace),
        "hwpx": build_hwpx_edit_workflow(workspace),
        "pptx": build_pptx_edit_workflow(workspace),
    }

    for file_type, workflow in workflows.items():
        nodes = _node_names(workflow)
        assert "edit" not in nodes
        assert expected[file_type] <= nodes


def _node_names(workflow) -> set[str]:
    return set(workflow.get_graph().nodes)
