from minial_agent.constants.display import DisplayInfo, standard_display


PATCH_TOOL_CALLS_DISPLAY = DisplayInfo(
    label="도구 호출 정리",
    running_message="AGENT가 도구 호출을 정리합니다.",
    completed_message="AGENT가 도구 호출 정리를 완료했습니다.",
    error_message="AGENT가 도구 호출 정리 중 오류가 발생했습니다.",
    pending_message="AGENT가 도구 호출 정리를 준비합니다.",
)

FILESYSTEM_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="파일 작업 준비",
    running_message="AGENT가 파일 작업 환경을 준비합니다.",
    completed_message="AGENT가 파일 작업 환경 준비를 완료했습니다.",
    error_message="AGENT가 파일 작업 환경 준비 중 오류가 발생했습니다.",
    pending_message="AGENT가 파일 작업 환경 준비를 확인합니다.",
)

SUBAGENT_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="서브에이전트 준비",
    running_message="AGENT가 서브에이전트 연결을 준비합니다.",
    completed_message="AGENT가 서브에이전트 준비를 완료했습니다.",
    error_message="AGENT가 서브에이전트 준비 중 오류가 발생했습니다.",
    pending_message="AGENT가 서브에이전트 준비를 확인합니다.",
)

SUMMARIZATION_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="대화 요약 정리",
    running_message="AGENT가 대화 맥락을 요약합니다.",
    completed_message="AGENT가 대화 요약 정리를 완료했습니다.",
    error_message="AGENT가 대화 요약 정리 중 오류가 발생했습니다.",
    pending_message="AGENT가 대화 요약 정리를 준비합니다.",
)

HITL_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="승인 확인",
    running_message="AGENT가 사용자 승인 필요 여부를 확인합니다.",
    completed_message="AGENT가 승인 확인을 완료했습니다.",
    error_message="AGENT가 승인 확인 중 오류가 발생했습니다.",
    pending_message="AGENT가 승인 확인을 준비합니다.",
)

SKILLS_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="스킬 확인",
    running_message="AGENT가 workspace 스킬을 확인합니다.",
    completed_message="AGENT가 workspace 스킬 확인을 완료했습니다.",
    error_message="AGENT가 workspace 스킬 확인 중 오류가 발생했습니다.",
    pending_message="AGENT가 workspace 스킬 확인을 준비합니다.",
)

OFFICE_BINARY_READ_GUARD_DISPLAY = DisplayInfo(
    label="문서 읽기 보호",
    running_message="AGENT가 문서 읽기 방식을 확인합니다.",
    completed_message="AGENT가 문서 읽기 방식 확인을 완료했습니다.",
    error_message="AGENT가 문서 읽기 방식 확인 중 오류가 발생했습니다.",
    pending_message="AGENT가 문서 읽기 방식 확인을 준비합니다.",
)

INTERNAL_MIDDLEWARE_DISPLAY = DisplayInfo(
    label="내부 작업",
    running_message="AGENT가 내부 작업을 진행합니다.",
    completed_message="AGENT가 내부 작업을 완료했습니다.",
    error_message="AGENT가 내부 작업 중 오류가 발생했습니다.",
    pending_message="AGENT가 내부 작업을 준비합니다.",
)


TOOL_DISPLAY_MAP: dict[str, DisplayInfo] = {
    "write_file": DisplayInfo(
        label="파일 작성",
        running_message="AGENT가 파일 작성을 시작합니다.",
        completed_message="AGENT가 파일 작성을 완료했습니다.",
        error_message="AGENT가 파일 작성 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 작성을 준비합니다.",
    ),
    "edit_file": DisplayInfo(
        label="파일 수정",
        running_message="AGENT가 파일 수정을 시작합니다.",
        completed_message="AGENT가 파일 수정을 완료했습니다.",
        error_message="AGENT가 파일 수정 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 수정을 준비합니다.",
    ),
    "read_file": DisplayInfo(
        label="파일 읽기",
        running_message="AGENT가 파일 읽기를 시작합니다.",
        completed_message="AGENT가 파일 읽기를 완료했습니다.",
        error_message="AGENT가 파일 읽기 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 읽기를 준비합니다.",
    ),
    "ls": DisplayInfo(
        label="파일 목록 확인",
        running_message="AGENT가 파일 목록 확인을 시작합니다.",
        completed_message="AGENT가 파일 목록 확인을 완료했습니다.",
        error_message="AGENT가 파일 목록 확인 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 목록 확인을 준비합니다.",
    ),
    "grep": DisplayInfo(
        label="파일 내용 검색",
        running_message="AGENT가 파일 내용 검색을 시작합니다.",
        completed_message="AGENT가 파일 내용 검색을 완료했습니다.",
        error_message="AGENT가 파일 내용 검색 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 내용 검색을 준비합니다.",
    ),
    "glob": DisplayInfo(
        label="파일 검색",
        running_message="AGENT가 파일 검색을 시작합니다.",
        completed_message="AGENT가 파일 검색을 완료했습니다.",
        error_message="AGENT가 파일 검색 중 오류가 발생했습니다.",
        pending_message="AGENT가 파일 검색을 준비합니다.",
    ),
    "execute": DisplayInfo(
        label="명령 실행",
        running_message="AGENT가 명령 실행을 시작합니다.",
        completed_message="AGENT가 명령 실행을 완료했습니다.",
        error_message="AGENT가 명령 실행 중 오류가 발생했습니다.",
        pending_message="AGENT가 명령 실행을 준비합니다.",
    ),
    "task": DisplayInfo(
        label="서브에이전트 위임",
        running_message="AGENT가 서브에이전트 위임을 시작합니다.",
        completed_message="AGENT가 서브에이전트 위임을 완료했습니다.",
        error_message="AGENT가 서브에이전트 위임 중 오류가 발생했습니다.",
        pending_message="AGENT가 서브에이전트 위임을 준비합니다.",
    ),
    "PatchToolCallsMiddleware": PATCH_TOOL_CALLS_DISPLAY,
    "PatchToolCallsMiddleware.before_agent": PATCH_TOOL_CALLS_DISPLAY,
    "PatchToolCallsMiddleware.after_agent": PATCH_TOOL_CALLS_DISPLAY,
    "FilesystemMiddleware": FILESYSTEM_MIDDLEWARE_DISPLAY,
    "FilesystemMiddleware.before_agent": FILESYSTEM_MIDDLEWARE_DISPLAY,
    "FilesystemMiddleware.after_agent": FILESYSTEM_MIDDLEWARE_DISPLAY,
    "SubAgentMiddleware": SUBAGENT_MIDDLEWARE_DISPLAY,
    "SubAgentMiddleware.before_agent": SUBAGENT_MIDDLEWARE_DISPLAY,
    "SubAgentMiddleware.after_agent": SUBAGENT_MIDDLEWARE_DISPLAY,
    "SummarizationMiddleware": SUMMARIZATION_MIDDLEWARE_DISPLAY,
    "SummarizationMiddleware.before_agent": SUMMARIZATION_MIDDLEWARE_DISPLAY,
    "SummarizationMiddleware.after_agent": SUMMARIZATION_MIDDLEWARE_DISPLAY,
    "HumanInTheLoopMiddleware": HITL_MIDDLEWARE_DISPLAY,
    "HumanInTheLoopMiddleware.before_agent": HITL_MIDDLEWARE_DISPLAY,
    "HumanInTheLoopMiddleware.after_agent": HITL_MIDDLEWARE_DISPLAY,
    "SkillsMiddleware": SKILLS_MIDDLEWARE_DISPLAY,
    "SkillsMiddleware.before_agent": SKILLS_MIDDLEWARE_DISPLAY,
    "SkillsMiddleware.after_agent": SKILLS_MIDDLEWARE_DISPLAY,
    "OfficeBinaryReadGuardMiddleware": OFFICE_BINARY_READ_GUARD_DISPLAY,
    "OfficeBinaryReadGuardMiddleware.before_agent": OFFICE_BINARY_READ_GUARD_DISPLAY,
    "OfficeBinaryReadGuardMiddleware.after_agent": OFFICE_BINARY_READ_GUARD_DISPLAY,
    "get_today": DisplayInfo(
        label="오늘 날짜 확인",
        running_message="AGENT가 오늘 날짜를 확인합니다.",
        completed_message="AGENT가 오늘 날짜 확인을 완료했습니다.",
        error_message="AGENT가 오늘 날짜 확인 중 오류가 발생했습니다.",
        pending_message="AGENT가 오늘 날짜 확인을 준비합니다.",
    ),
    "read_docx_file": standard_display("DOCX 읽기"),
    "read_hwpx_file": standard_display("HWPX 읽기"),
    "read_pptx_file": standard_display("PPTX 읽기"),
    "read_pdf_file": standard_display("PDF 읽기"),
    "read_xlsx_file": standard_display("XLSX 읽기"),
    "edit_docx": standard_display("DOCX 수정"),
    "edit_hwpx": standard_display("HWPX 수정"),
    "edit_pptx": standard_display("PPTX 수정"),
    "edit_xlsx": standard_display("XLSX 수정"),
}


def get_tool_display(name: str | None) -> DisplayInfo:
    tool_name = name or "작업"
    display = TOOL_DISPLAY_MAP.get(tool_name)
    if display:
        return display

    if _is_middleware_name(tool_name):
        return INTERNAL_MIDDLEWARE_DISPLAY

    label = tool_name
    return DisplayInfo(
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


def _is_middleware_name(name: str) -> bool:
    return (
        "Middleware" in name
        or name.endswith(".before_agent")
        or name.endswith(".after_agent")
    )
