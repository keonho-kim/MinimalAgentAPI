from pathlib import Path
from typing import Any

from minial_agent.constants.agent_mapper import is_agent_name

from minial_agent.api.agent.events.activity.constants import (
    HITL_TOOL_NAMES,
    WRITE_FILE_PARENT_COMPLETED_MESSAGE,
    WRITE_FILE_PARENT_RUNNING_MESSAGE,
)
from minial_agent.api.agent.events.activity.context import (
    get_skill_read_context,
    get_write_file_parent_context,
    skill_read_message,
)
from minial_agent.api.agent.events.activity.display import activity_display
from minial_agent.api.agent.events.activity.summary import (
    event_metadata_summary,
    output_looks_error,
    public_summary,
    string_value,
    summarize_activity,
)
from minial_agent.api.agent.events.serialization import object_or_empty


class ActivityEventBuilder:
    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self._workspace_root = (
            Path(workspace_root).resolve() if workspace_root else None
        )
        self._activity_contexts: dict[str, dict[str, Any]] = {}
        self._activity_inputs: dict[str, Any] = {}
        self._active_delegation_runs: set[str] = set()

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

        summary = summarize_activity(name, input_value, output)
        folder_context = get_write_file_parent_context(
            self._workspace_root,
            name,
            input_value,
        )
        skill_context = get_skill_read_context(name, input_value)

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

        label, message = activity_display(name, status, summary)
        if skill_context:
            label = "스킬 읽기"
            message = skill_read_message(skill_context["skill_name"], status)
        elif folder_context and status == "running":
            message = WRITE_FILE_PARENT_RUNNING_MESSAGE
        elif folder_context and status == "completed":
            if folder_context["real_parent_path"].exists() and not output_looks_error(
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
            "summary": event_metadata_summary(raw),
        }

    def create_intermediate_model_output(
        self,
        raw: dict[str, Any],
        text: str,
    ) -> dict[str, Any]:
        run_id = raw.get("run_id") or "model"
        return {
            "kind": "activity",
            "type": "model_output",
            "id": f"{run_id}:intermediate-output",
            "sourceEvent": raw.get("event"),
            "runId": run_id,
            "parentIds": raw.get("parent_ids") or [],
            "name": raw.get("name") or "model",
            "label": "중간 응답",
            "message": "하위 에이전트의 중간 응답을 접어 보관했습니다.",
            "status": "completed",
            "summary": public_summary(
                {
                    **event_metadata_summary(raw),
                    "intermediateText": text,
                }
            ),
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
            "summary": public_summary(summary),
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
        summary = summarize_activity(name, input_value)
        skill_context = get_skill_read_context(name, input_value)
        label, message = activity_display(name, status, summary)
        if skill_context:
            summary.update(skill_context["summary"])
            label = "스킬 읽기"
            message = skill_read_message(skill_context["skill_name"], status)
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
            "summary": summary,
        }

    def normalize_visible_chain(
        self,
        raw: dict[str, Any],
        event_name: str,
    ) -> dict[str, Any] | None:
        name = raw.get("name") or ""
        if _is_internal_middleware_name(name):
            return None

        if name == "task" or "subagent" in name.lower():
            return self._create_delegation_chain(raw, event_name)

        if name.startswith(("answer_", "edit_")):
            return None

        if not is_agent_name(name):
            return None

        return self._create_agent_step_chain(raw, event_name)

    def _create_delegation_chain(
        self,
        raw: dict[str, Any],
        event_name: str,
    ) -> dict[str, Any]:
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        status = "running" if event_name.endswith("_start") else "completed"
        activity = self.create(
            raw,
            "subagent",
            status,
            data.get("input"),
            data.get("output"),
        )
        delegation_run_id = string_value(activity.get("runId"))
        if delegation_run_id:
            activity["summary"] = {
                **object_or_empty(activity.get("summary")),
                "delegationRunId": delegation_run_id,
            }
            if status == "running":
                self._active_delegation_runs.add(delegation_run_id)
            else:
                self._active_delegation_runs.discard(delegation_run_id)

        return activity

    def _create_agent_step_chain(
        self,
        raw: dict[str, Any],
        event_name: str,
    ) -> dict[str, Any]:
        data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        activity = self.create(
            raw,
            "agent_step",
            "running" if event_name.endswith("_start") else "completed",
            data.get("input"),
            data.get("output"),
        )
        delegation_run_id = self._delegation_run_id(raw.get("parent_ids"))
        if delegation_run_id:
            activity["summary"] = {
                **object_or_empty(activity.get("summary")),
                "delegationRunId": delegation_run_id,
            }

        return activity

    def _delegation_run_id(self, parent_ids: Any) -> str | None:
        if not isinstance(parent_ids, list):
            return None

        for parent_id in parent_ids:
            if isinstance(parent_id, str) and parent_id in self._active_delegation_runs:
                return parent_id

        return None


def _is_internal_middleware_name(name: str) -> bool:
    return (
        "Middleware" in name
        or name.endswith(".before_agent")
        or name.endswith(".after_agent")
    )
