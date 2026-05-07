import shutil
from pathlib import Path
from typing import Any

from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact

from minial_agent.agents.domain.office_file_editor.utils.edit_protocol import (
    OperationSelector,
    SlotFiller,
    fill_slots,
    require_slots,
    select_operation,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.utils.editing import apply_xlsx_edit
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.workflow.edit.prompts import OPERATION_PROMPT, SLOT_PROMPT


def resolve_xlsx_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return file_registry.resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="xlsx",
    )


def build_xlsx_edit_spec(
    *,
    instruction: str,
    artifact: ResolvedUploadArtifact,
    operation_selector: OperationSelector | None = None,
    slot_filler: SlotFiller | None = None,
) -> dict[str, Any]:
    operation = select_operation(
        instruction=instruction,
        prompt=OPERATION_PROMPT,
        selector=operation_selector,
    )
    allowed_operations = {"write_values", "write_formulas", "add_sheet", "format_range"}
    if operation not in allowed_operations:
        raise ValueError(f"Unsupported XLSX edit operation: {operation}")
    slots = fill_slots(
        operation=operation,
        instruction=instruction,
        prompt=SLOT_PROMPT,
        slot_filler=slot_filler,
    )
    _validate_xlsx_slots(operation=operation, slots=slots, artifact=artifact)
    return {
        "operation": operation,
        "slots": slots,
    }


def _validate_xlsx_slots(
    *,
    operation: str,
    slots: dict[str, str],
    artifact: ResolvedUploadArtifact,
) -> None:
    require_slots(operation=operation, slots=slots, required={"SHEET"})
    if operation == "add_sheet":
        if slots["SHEET"] in _xlsx_sheet_names(artifact):
            raise ValueError(f"XLSX sheet already exists: {slots['SHEET']}")
        return

    slots["SHEET"] = _resolve_xlsx_sheet_name(artifact, slots["SHEET"])
    if operation == "write_values":
        if "CELL" not in slots and "START_CELL" not in slots:
            raise ValueError("write_values requires CELL or START_CELL.")
        if not {"VALUE", "TEXT", "VALUES"} & set(slots):
            raise ValueError("write_values requires VALUE, TEXT, or VALUES.")
    elif operation == "write_formulas":
        if "CELL" not in slots and "START_CELL" not in slots:
            raise ValueError("write_formulas requires CELL or START_CELL.")
        if not {"FORMULA", "FORMULA_PATTERN"} & set(slots):
            raise ValueError("write_formulas requires FORMULA or FORMULA_PATTERN.")
    elif operation == "format_range":
        require_slots(operation=operation, slots=slots, required={"RANGE"})
        if not {"FILL", "BOLD"} & set(slots):
            raise ValueError("format_range requires FILL or BOLD.")


def _resolve_xlsx_sheet_name(
    artifact: ResolvedUploadArtifact,
    requested_sheet: str,
) -> str:
    sheet_names = _xlsx_sheet_names(artifact)
    if not sheet_names or requested_sheet in sheet_names:
        return requested_sheet
    for sheet_name in sheet_names:
        if sheet_name.lower() == requested_sheet.lower():
            return sheet_name
    raise ValueError(f"XLSX sheet not found: {requested_sheet}")


def _xlsx_sheet_names(artifact: ResolvedUploadArtifact) -> set[str]:
    workbook_index = artifact.workbook_index or {}
    sheets = workbook_index.get("sheets", [])
    if not isinstance(sheets, list):
        return set()
    return {
        str(sheet.get("sheet_name", ""))
        for sheet in sheets
        if str(sheet.get("sheet_name", ""))
    }


def apply_xlsx_edit_spec(
    *,
    artifact: ResolvedUploadArtifact,
    edit_spec: dict[str, Any],
    edited_path: Path,
) -> list[dict[str, Any]]:
    shutil.copyfile(artifact.source_path, edited_path)
    return apply_xlsx_edit(
        path=edited_path,
        operation=str(edit_spec["operation"]),
        slots=edit_spec["slots"],
        source_filename=artifact.visible_name,
    )


def register_xlsx_edit_result(
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
