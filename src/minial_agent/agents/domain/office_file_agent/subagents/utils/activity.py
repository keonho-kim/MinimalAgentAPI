from typing import Any

from langchain_core.callbacks.manager import dispatch_custom_event


def emit_workflow_event(
    *,
    name: str,
    label: str,
    message: str,
    status: str = "running",
    summary: dict[str, Any] | None = None,
) -> None:
    try:
        dispatch_custom_event(
            "office_workflow",
            {
                "type": "workflow",
                "name": name,
                "label": label,
                "message": message,
                "status": status,
                "summary": summary or {},
            },
        )
    except RuntimeError:
        return


def emit_read_step(
    *,
    file_type: str,
    step: str,
    message: str,
    status: str = "running",
    summary: dict[str, Any] | None = None,
) -> None:
    next_summary = {
        "operation": "read",
        "fileType": file_type,
        **(summary or {}),
    }
    emit_workflow_event(
        name=f"{file_type}_read_{step}",
        label=f"{file_type.upper()} 읽기",
        message=message,
        status=status,
        summary=next_summary,
    )


def emit_edit_step(
    *,
    file_type: str,
    step: str,
    message: str,
    status: str = "running",
    summary: dict[str, Any] | None = None,
) -> None:
    emit_workflow_event(
        name=f"{file_type}_edit_{step}",
        label=f"{file_type.upper()} 수정",
        message=message,
        status=status,
        summary=summary,
    )
