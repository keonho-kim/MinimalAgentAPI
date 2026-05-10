import json
import shutil
from pathlib import Path
from typing import Any

from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.prompts import (
    OPERATION_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.workflow.edit.state import (
    PptxEditState,
)
from minial_agent.agents.utils.activity import emit_edit_step
from minial_agent.agents.utils.runtime import invoke_text_llm
from minial_agent.common.utils import file_registry
from minial_agent.integrations.pptx.ingest import load_or_ingest_pptx_deck
from minial_agent.integrations.pptx.model import PptxOperation
from minial_agent.integrations.pptx.operations import apply_pptx_operations
from minial_agent.integrations.pptx.store import PptxDeckStore, pptx_db_path
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact
from minial_agent.integrations.upload.storage import unique_path

OperationGenerator = Any


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
    workspace: UploadWorkspace,
    artifact: ResolvedUploadArtifact,
    instruction: str,
    operation_generator: OperationGenerator | None = None,
) -> dict[str, Any]:
    deck = load_or_ingest_pptx_deck(
        cache_dir=workspace.cache_dir,
        source_path=artifact.source_path,
    )
    deck_summary = _deck_summary(deck.model_dump(mode="json"))
    raw_operations = (
        operation_generator(instruction, deck_summary)
        if operation_generator
        else invoke_text_llm(
            OPERATION_PROMPT.format(
                instruction=instruction,
                deck_summary=json.dumps(deck_summary, ensure_ascii=False),
            ),
            disable_streaming=True,
        )
    )
    operations = _parse_operations(raw_operations)
    return {
        "deck_revision": deck.revision,
        "operations": [operation.model_dump(mode="json") for operation in operations],
    }


def apply_pptx_edit_spec(
    *,
    workspace: UploadWorkspace,
    artifact: ResolvedUploadArtifact,
    edit_spec: dict[str, Any],
    edited_path: Path,
) -> list[dict[str, Any]]:
    shutil.copyfile(artifact.source_path, edited_path)
    source_deck = load_or_ingest_pptx_deck(
        cache_dir=workspace.cache_dir,
        source_path=artifact.source_path,
    )
    store = PptxDeckStore(pptx_db_path(workspace.cache_dir, edited_path))
    store.save(
        source_deck,
        source_stat=_source_stat(edited_path),
        revision=int(edit_spec["deck_revision"]),
    )
    operations = [
        PptxOperation.model_validate(operation)
        for operation in edit_spec["operations"]
    ]
    result = apply_pptx_operations(
        cache_dir=workspace.cache_dir,
        source_path=edited_path,
        expected_revision=int(edit_spec["deck_revision"]),
        origin="ai",
        operations=operations,
    )
    return [
        {
            "source_file": artifact.visible_name,
            "operation": operation["type"],
            "slide_id": operation.get("slideId"),
            "element_id": operation.get("elementId"),
            "changed_slides": result.changed_slide_ids,
            "rejected": result.rejected_operations,
        }
        for operation in edit_spec["operations"]
    ]


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
    workspace: UploadWorkspace,
    operation_generator: OperationGenerator | None,
) -> PptxEditState:
    emit_edit_step(
        file_type="pptx",
        step="spec",
        message="PPTX 수정 방법을 정리합니다.",
        details={"path": state["artifact"].visible_name},
    )
    edit_spec = build_pptx_edit_spec(
        workspace=workspace,
        artifact=state["artifact"],
        instruction=state.get("instruction", ""),
        operation_generator=operation_generator,
    )
    emit_edit_step(
        file_type="pptx",
        step="spec",
        message=f"PPTX 수정 작업 {len(edit_spec['operations'])}개를 준비했습니다.",
        status="completed",
        details={
            "path": state["artifact"].visible_name,
            "description": f"{len(edit_spec['operations'])} operations",
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
        workspace=workspace,
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


def _parse_operations(raw: str) -> list[PptxOperation]:
    text = raw.strip()
    if text.startswith("```"):
        text = (
            text.removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("PPTX operation generator returned invalid JSON.") from exc
    if not isinstance(payload, list):
        raise ValueError("PPTX operation generator must return a JSON array.")
    return [PptxOperation.model_validate(item) for item in payload]


def _deck_summary(deck: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": deck["id"],
        "revision": deck["revision"],
        "canvas": deck["canvas"],
        "slides": [
            {
                "id": slide["id"],
                "index": slide["index"],
                "title": slide["title"],
                "notes": slide["notes"],
                "elements": [
                    {
                        "id": element["id"],
                        "type": element["type"],
                        "role": element["role"],
                        "content": element["content"],
                        "manualOverrides": element["manualOverrides"],
                    }
                    for element in slide["elements"]
                ],
            }
            for slide in deck["slides"]
        ],
    }


def _source_stat(source_path: Path) -> dict[str, int | str]:
    stat = source_path.stat()
    return {
        "path": str(source_path.resolve()),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
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
