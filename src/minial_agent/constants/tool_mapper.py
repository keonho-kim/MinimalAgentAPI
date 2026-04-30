from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDisplay:
    label: str
    running_message: str
    completed_message: str
    error_message: str
    pending_message: str


TOOL_DISPLAY_MAP: dict[str, ToolDisplay] = {
    "write_file": ToolDisplay(
        label="파일 작성",
        running_message="AGENT가 파일 작성을 시작합니다.",
        completed_message="AGENT가 파일 작성을 완료했습니다.",
        error_message="AGENT가 파일 작성 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 작성을 준비합니다.",
    ),
    "edit_file": ToolDisplay(
        label="파일 수정",
        running_message="AGENT가 파일 수정을 시작합니다.",
        completed_message="AGENT가 파일 수정을 완료했습니다.",
        error_message="AGENT가 파일 수정 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 수정을 준비합니다.",
    ),
    "read_file": ToolDisplay(
        label="파일 읽기",
        running_message="AGENT가 파일 읽기를 시작합니다.",
        completed_message="AGENT가 파일 읽기를 완료했습니다.",
        error_message="AGENT가 파일 읽기 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 읽기를 준비합니다.",
    ),
    "ls": ToolDisplay(
        label="파일 목록 확인",
        running_message="AGENT가 파일 목록 확인을 시작합니다.",
        completed_message="AGENT가 파일 목록 확인을 완료했습니다.",
        error_message="AGENT가 파일 목록 확인 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 목록 확인을 준비합니다.",
    ),
    "grep": ToolDisplay(
        label="파일 내용 검색",
        running_message="AGENT가 파일 내용 검색을 시작합니다.",
        completed_message="AGENT가 파일 내용 검색을 완료했습니다.",
        error_message="AGENT가 파일 내용 검색 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 내용 검색을 준비합니다.",
    ),
    "glob": ToolDisplay(
        label="파일 검색",
        running_message="AGENT가 파일 검색을 시작합니다.",
        completed_message="AGENT가 파일 검색을 완료했습니다.",
        error_message="AGENT가 파일 검색 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 검색을 준비합니다.",
    ),
    "execute": ToolDisplay(
        label="명령 실행",
        running_message="AGENT가 명령 실행을 시작합니다.",
        completed_message="AGENT가 명령 실행을 완료했습니다.",
        error_message="AGENT가 명령 실행 중 오류가 발생했습니다.",
        pending_message="AGENT가 명령 실행을 준비합니다.",
    ),
    "task": ToolDisplay(
        label="서브에이전트 위임",
        running_message="AGENT가 서브에이전트 위임을 시작합니다.",
        completed_message="AGENT가 서브에이전트 위임을 완료했습니다.",
        error_message="AGENT가 서브에이전트 위임 중 오류가 발생했습니다.",
        pending_message="AGENT가 서브에이전트 위임을 준비합니다.",
    ),
}


def get_tool_display(name: str | None) -> ToolDisplay:
    tool_name = name or "작업"
    display = TOOL_DISPLAY_MAP.get(tool_name)
    if display:
        return display

    label = tool_name
    return ToolDisplay(
        label=label,
        running_message=f"AGENT가 {label} 작업을 시작합니다.",
        completed_message=f"AGENT가 {label} 작업을 완료했습니다.",
        error_message=f"AGENT가 {label} 작업 중 오류가 발생했습니다.",
        pending_message=f"AGENT가 {label} 작업을 준비합니다.",
    )


def get_tool_label(name: str | None) -> str:
    return get_tool_display(name).label


def get_tool_message(name: str | None, status: str) -> str:
    display = get_tool_display(name)

    if status == "running":
        return display.running_message
    if status == "completed":
        return display.completed_message
    if status == "error":
        return display.error_message

    return display.pending_message
