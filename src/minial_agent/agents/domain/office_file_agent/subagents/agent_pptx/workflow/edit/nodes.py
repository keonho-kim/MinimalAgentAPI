import shutil
from pathlib import Path
from typing import Any

from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.domain.office_file_agent.subagents.utils.edit_protocol import (
    OperationSelector,
    SlotFiller,
    fill_slots,
    require_slots,
    select_operation,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.utils.editing import apply_pptx_edit
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.workflow.edit.prompts import OPERATION_PROMPT, SLOT_PROMPT


def resolve_pptx_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return file_registry.resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="pptx",
    )


def build_pptx_edit_spec(
    *,
    instruction: str,
    operation_selector: OperationSelector | None = None,
    slot_filler: SlotFiller | None = None,
) -> dict[str, Any]:
    operation = select_operation(
        instruction=instruction,
        prompt=OPERATION_PROMPT,
        selector=operation_selector,
    )
    allowed_operations = {"replace_slide_title", "replace_slide_text", "add_slide"}
    if operation not in allowed_operations:
        raise ValueError(f"Unsupported PPTX edit operation: {operation}")
    slots = fill_slots(
        operation=operation,
        instruction=instruction,
        prompt=SLOT_PROMPT,
        slot_filler=slot_filler,
    )
    required_slots = {
        "replace_slide_title": {"PAGE", "TITLE"},
        "replace_slide_text": {"PAGE", "TEXT"},
        "add_slide": {"TITLE"},
    }
    require_slots(operation=operation, slots=slots, required=required_slots[operation])
    return {
        "operation": operation,
        "slots": slots,
    }


def apply_pptx_edit_spec(
    *,
    artifact: ResolvedUploadArtifact,
    edit_spec: dict[str, Any],
    edited_path: Path,
) -> list[dict[str, Any]]:
    shutil.copyfile(artifact.source_path, edited_path)
    return apply_pptx_edit(
        path=edited_path,
        operation=str(edit_spec["operation"]),
        slots=edit_spec["slots"],
        source_filename=artifact.visible_name,
    )


def register_pptx_edit_result(
    *,
    workspace: UploadWorkspace,
    artifact: ResolvedUploadArtifact,
    edited_path: Path,
    changed_items: list[dict[str, Any]],
) -> dict[str, Any]:
    edited_file, _manifest = file_registry.register_edited_file(
        workspace=workspace,
        source_artifact=artifact,
        edited_path=edited_path,
        changed_items=changed_items,
    )
    return {
        "summary": f"{artifact.visible_name} 수정본을 생성했습니다.",
        "edited_file": {
            "file_id": edited_file.file_id,
            "filename": edited_file.filename,
            "download_url": edited_file.download_url,
        },
        "changed_items": changed_items,
    }
