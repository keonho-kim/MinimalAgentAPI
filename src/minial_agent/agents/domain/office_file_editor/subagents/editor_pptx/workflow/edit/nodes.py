import json
import shutil
from pathlib import Path
from typing import Any

from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact
from minial_agent.integrations.upload.storage import unique_path

from minial_agent.agents.utils.activity import emit_edit_step
from minial_agent.agents.domain.office_file_editor.utils.edit_protocol import (
    OperationSelector,
    SlotFiller,
    fill_slots,
    require_slots,
    select_operation,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.utils.editing import apply_pptx_edit
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.prompts import OPERATION_PROMPT, SLOT_PROMPT
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.state import PptxEditState


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


def resolve_pptx_artifact_node(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="resolve",
        message="수정할 PPTX 파일을 확인합니다.",
        details={"path": state["file_ref"]},
    )
    artifact = resolve_pptx_artifact(workspace, state["file_ref"])
    emit_edit_step(
        file_type="pptx",
        step="resolve",
        message="PPTX 파일 확인을 완료했습니다.",
        status="completed",
        details={"path": artifact.visible_name},
    )
    return {"artifact": artifact}


def build_pptx_edit_spec_node(
    state: PptxEditState,
    *,
    operation_selector: OperationSelector | None,
    slot_filler: SlotFiller | None,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="spec",
        message="PPTX 수정 방법을 정리합니다.",
        details={"path": state["artifact"].visible_name},
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
        details={
            "path": state["artifact"].visible_name,
            "description": str(edit_spec["operation"]),
        },
    )
    return {"edit_spec": edit_spec}


def apply_pptx_edit_spec_node(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="apply",
        message="PPTX 수정 내용을 파일에 적용합니다.",
        details={"path": state["artifact"].visible_name},
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
        details={
            "path": state["artifact"].visible_name,
            "result": f"{len(changed_items)} changes",
        },
    )
    return {
        "edited_path": edited_path,
        "changed_items": changed_items,
    }


def register_pptx_edit_result_node(
    state: PptxEditState,
    *,
    workspace: UploadWorkspace,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="register",
        message="PPTX 수정본을 등록하고 다운로드 정보를 준비합니다.",
        details={"path": state["artifact"].visible_name},
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
        details={
            "path": result.get("edited_file", {}).get("filename"),
            "result": result.get("edited_file", {}).get("download_url"),
        },
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
