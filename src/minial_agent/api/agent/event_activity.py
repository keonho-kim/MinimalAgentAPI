import ast
import json
from pathlib import Path
import re
from typing import Any

from minial_agent.constants.tool_mapper import get_tool_label, get_tool_message

from minial_agent.api.agent.event_extraction import jsonable_mapping, object_or_empty

WRITE_FILE_PARENT_RUNNING_MESSAGE = (
    "AGENT가 필요한 폴더를 만들고 파일 작성을 시작합니다."
)
WRITE_FILE_PARENT_COMPLETED_MESSAGE = (
    "AGENT가 필요한 폴더를 만들고 파일 작성을 완료했습니다."
)
HITL_TOOL_NAMES = {
    "write_file",
    "edit_file",
    "edit_docx",
    "edit_hwpx",
    "edit_pptx",
    "edit_xlsx",
}
SKILL_READ_PENDING_MESSAGE = "AGENT가 스킬 읽기를 준비합니다."
SKILL_READ_RUNNING_MESSAGE = "AGENT가 {skill_name} 스킬을 읽습니다."
SKILL_READ_COMPLETED_MESSAGE = "AGENT가 {skill_name} 스킬을 읽었습니다."
SKILL_READ_ERROR_MESSAGE = "AGENT가 {skill_name} 스킬을 읽는 중 오류가 발생했습니다."


class ActivityEventBuilder:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._workspace_root = (
            Path(workspace_root).resolve() if workspace_root else None
        )
        self._activity_contexts: dict[str, dict[str, Any]] = {}
        self._activity_inputs: dict[str, Any] = {}

    def create(
        self,
        raw: dict[str, Any],
        activity_type: str,
        status: str,
        input_value: Any = None,
        output: Any = None,
    ) -> dict[str, Any]:
        name = raw.get("name") or activity_type
        activity_id = raw.get("run_id") or f"{activity_type}:{name}"
        if (
            input_value is None
            and isinstance(activity_id, str)
            and activity_id in self._activity_inputs
        ):
            input_value = self._activity_inputs[activity_id]

        summary = _summarize_activity(name, input_value, output)
        folder_context = self._get_write_file_parent_context(name, input_value)
        skill_context = _get_skill_read_context(name, input_value)

        if isinstance(activity_id, str):
            stored_context = self._activity_contexts.get(activity_id)
            if (
                not folder_context
                and stored_context
                and stored_context.get("context_type") == "write_file_parent"
            ):
                folder_context = stored_context
            if (
                not skill_context
                and stored_context
                and stored_context.get("context_type") == "skill_read"
            ):
                skill_context = stored_context

        if folder_context:
            summary.update(folder_context["summary"])
            if status == "running" and isinstance(activity_id, str):
                self._activity_contexts[activity_id] = folder_context
        if skill_context:
            summary.update(skill_context["summary"])
            if status == "running" and isinstance(activity_id, str):
                self._activity_contexts[activity_id] = skill_context

        message = get_tool_message(name, status)
        label = get_tool_label(name)
        if skill_context:
            label = "스킬 읽기"
            message = _skill_read_message(skill_context["skill_name"], status)
        elif folder_context and status == "running":
            message = WRITE_FILE_PARENT_RUNNING_MESSAGE
        elif folder_context and status == "completed":
            if folder_context["real_parent_path"].exists() and not _output_looks_error(
                output
            ):
                summary["parentDirectoryCreated"] = True
                message = WRITE_FILE_PARENT_COMPLETED_MESSAGE
        elif folder_context and status == "error":
            summary["parentDirectoryCreated"] = False

        if name in HITL_TOOL_NAMES and status in {"pending", "running"}:
            summary["requiresApproval"] = True
            summary.setdefault("description", "승인이 필요한 파일 변경 작업입니다.")

        if isinstance(activity_id, str) and status in {"pending", "running"}:
            if input_value is not None:
                self._activity_inputs[activity_id] = input_value

        if isinstance(activity_id, str) and status in {"completed", "error"}:
            self._activity_contexts.pop(activity_id, None)
            self._activity_inputs.pop(activity_id, None)

        return {
            "kind": "activity",
            "type": activity_type,
            "id": activity_id,
            "sourceEvent": raw.get("event"),
            "runId": activity_id,
            "parentIds": raw.get("parent_ids") or [],
            "name": name,
            "label": label,
            "message": message,
            "status": status,
            "input": input_value,
            "output": output,
            "summary": summary,
        }

    def create_model(self, raw: dict[str, Any], status: str) -> dict[str, Any]:
        run_id = raw.get("run_id") or f"model:{status}"
        return {
            "kind": "activity",
            "type": "model",
            "id": run_id,
            "sourceEvent": raw.get("event"),
            "runId": run_id,
            "parentIds": raw.get("parent_ids") or [],
            "name": raw.get("name") or "model",
            "label": "응답 생성",
            "message": (
                "AGENT가 요청을 분석합니다."
                if status == "running"
                else "AGENT가 답변을 정리합니다."
            ),
            "status": status,
            "summary": _event_metadata_summary(raw),
        }

    def create_custom(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = object_or_empty(raw.get("data"))
        summary = object_or_empty(data.get("summary"))
        name = str(data.get("name") or raw.get("name") or "custom")
        status = str(data.get("status") or "running")
        label = str(data.get("label") or "작업 진행")
        message = str(data.get("message") or "AGENT가 작업을 진행합니다.")

        raw_run_id = raw.get("run_id")
        activity_id = data.get("id") or (
            f"{raw_run_id}:{name}" if raw_run_id else f"custom:{name}"
        )

        return {
            "kind": "activity",
            "type": str(data.get("type") or "workflow"),
            "id": activity_id,
            "sourceEvent": raw.get("event"),
            "runId": raw.get("run_id"),
            "parentIds": raw.get("parent_ids") or [],
            "name": name,
            "label": label,
            "message": message,
            "status": status,
            "input": data.get("input"),
            "output": data.get("output"),
            "summary": summary,
        }

    def create_tool_intent(
        self,
        raw: dict[str, Any],
        run_id: Any,
        tool_call: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        name = tool_call.get("name") or "tool"
        input_value = tool_call.get("args")
        status = "pending"
        summary = _summarize_activity(name, input_value)
        skill_context = _get_skill_read_context(name, input_value)
        label = get_tool_label(name)
        message = get_tool_message(name, status)
        if skill_context:
            summary.update(skill_context["summary"])
            label = "스킬 읽기"
            message = _skill_read_message(skill_context["skill_name"], status)
        if name in HITL_TOOL_NAMES:
            summary["requiresApproval"] = True
            summary.setdefault("description", "승인이 필요한 파일 변경 작업입니다.")

        return {
            "kind": "activity",
            "type": "tool",
            "id": tool_call.get("id") or f"{run_id}:{tool_call.get('index', index)}",
            "sourceEvent": raw.get("event"),
            "runId": run_id,
            "parentIds": raw.get("parent_ids") or [],
            "name": name,
            "label": label,
            "message": message,
            "status": status,
            "input": input_value,
            "summary": summary,
        }

    def normalize_visible_chain(
        self,
        raw: dict[str, Any],
        event_name: str,
    ) -> dict[str, Any] | None:
        name = raw.get("name") or ""
        looks_like_subagent = (
            name == "task"
            or "subagent" in name.lower()
            or "agent" in name.lower()
            or name.startswith(("answer_", "edit_"))
        )

        if not looks_like_subagent:
            return None

        data = object_or_empty(raw.get("data"))
        return self.create(
            raw,
            "chain",
            "running" if event_name.endswith("_start") else "completed",
            data.get("input"),
            data.get("output"),
        )

    def _get_write_file_parent_context(
        self,
        name: str,
        input_value: Any,
    ) -> dict[str, Any] | None:
        if name != "write_file" or self._workspace_root is None:
            return None

        source = object_or_empty(input_value)
        virtual_path = source.get("file_path") or source.get("path")
        if not isinstance(virtual_path, str) or not virtual_path.strip():
            return None

        resolved_path = _resolve_workspace_virtual_path(
            self._workspace_root,
            virtual_path,
        )
        if resolved_path is None:
            return None

        parent_path = resolved_path.parent
        if parent_path == self._workspace_root or parent_path.exists():
            return None

        virtual_parent_path = _virtual_parent_path(virtual_path)
        return {
            "context_type": "write_file_parent",
            "real_parent_path": parent_path,
            "summary": {
                "createsParentDirectory": True,
                "parentPath": virtual_parent_path,
                "description": f"필요한 폴더: {virtual_parent_path}",
            },
        }


def _summarize_activity(
    name: str, input_value: Any, output: Any = None
) -> dict[str, Any]:
    source = object_or_empty(input_value)
    result = object_or_empty(output)
    skill_lines = _skill_metadata_lines(output)
    result_preview = None if skill_lines else _preview_value(output)
    summary = {
        "path": source.get("file_path")
        or source.get("path")
        or result.get("file_path")
        or result.get("path"),
        "command": source.get("command"),
        "query": source.get("query") or source.get("pattern"),
        "description": source.get("description"),
        "result": result_preview,
    }

    if skill_lines:
        summary["skills"] = skill_lines

    return summary


def _get_skill_read_context(
    name: str,
    input_value: Any,
) -> dict[str, Any] | None:
    if name != "read_file":
        return None

    source = object_or_empty(input_value)
    path = source.get("file_path") or source.get("path")
    if not isinstance(path, str):
        return None

    skill_name = _skill_name_from_path(path)
    if skill_name is None:
        return None

    return {
        "context_type": "skill_read",
        "skill_name": skill_name,
        "summary": {
            "skillName": skill_name,
            "path": f"/.agents/skills/{skill_name}/SKILL.md",
            "description": f"사용한 스킬: {skill_name}",
        },
    }


def _skill_name_from_path(path: str) -> str | None:
    normalized = path.strip().replace("\\", "/")
    prefixes = (
        "/.agents/skills/",
        ".agents/skills/",
    )
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue
        relative = normalized.removeprefix(prefix)
        parts = [part for part in relative.split("/") if part]
        if len(parts) == 2 and parts[1] == "SKILL.md" and parts[0]:
            return parts[0]
    return None


def _skill_read_message(skill_name: str, status: str) -> str:
    if status == "pending":
        return SKILL_READ_PENDING_MESSAGE
    if status == "running":
        return SKILL_READ_RUNNING_MESSAGE.format(skill_name=skill_name)
    if status == "completed":
        return SKILL_READ_COMPLETED_MESSAGE.format(skill_name=skill_name)
    if status == "error":
        return SKILL_READ_ERROR_MESSAGE.format(skill_name=skill_name)
    return f"AGENT가 {skill_name} 스킬을 확인합니다."


def _resolve_workspace_virtual_path(
    workspace_root: Path,
    virtual_path: str,
) -> Path | None:
    relative_path = virtual_path.strip().lstrip("/")
    if not relative_path:
        return None

    resolved_path = (workspace_root / relative_path).resolve()
    try:
        resolved_path.relative_to(workspace_root)
    except ValueError:
        return None

    return resolved_path


def _virtual_parent_path(virtual_path: str) -> str:
    normalized = "/" + virtual_path.strip().lstrip("/")
    parent = str(Path(normalized).parent)
    return "/" if parent == "." else parent


def _output_looks_error(output: Any) -> bool:
    output = jsonable_mapping(output)

    if isinstance(output, str):
        return "error" in output.lower()

    if isinstance(output, dict):
        error = output.get("error")
        return bool(error)

    return False


def _event_metadata_summary(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = object_or_empty(raw.get("metadata"))
    node = metadata.get("langgraph_node")
    model = metadata.get("ls_model_name") or metadata.get("model_name")
    return {
        "description": "모델 응답을 생성하는 단계입니다.",
        "node": node,
        "model": model,
    }


def _preview_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return _truncate(_tool_message_content(value) or value)

    if isinstance(value, dict):
        useful = (
            value.get("message")
            or value.get("error")
            or value.get("result")
            or value.get("output")
            or value.get("content")
            or value.get("file_path")
            or value.get("path")
        )
        return (
            _truncate(str(useful))
            if useful
            else _truncate(json.dumps(value, ensure_ascii=False))
        )

    return _truncate(str(value))


def _skill_metadata_lines(value: Any) -> list[str]:
    value = jsonable_mapping(value)
    if not isinstance(value, dict):
        return []

    metadata = value.get("skills_metadata")
    if not isinstance(metadata, list):
        return []

    lines = []
    for item in metadata:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        description = item.get("description")
        if isinstance(name, str) and name.strip():
            if isinstance(description, str) and description.strip():
                lines.append(f"{name.strip()}: {description.strip()}")
            else:
                lines.append(name.strip())

    return lines


def _tool_message_content(value: str) -> str | None:
    match = re.search(
        r"content=(?P<content>'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")\s+name=",
        value,
    )
    if not match:
        return None

    try:
        content = ast.literal_eval(match.group("content"))
    except (SyntaxError, ValueError):
        return None

    return content if isinstance(content, str) else None


def _truncate(value: str, max_length: int = 700) -> str:
    if len(value) <= max_length:
        return value

    return f"{value[:max_length]}..."
