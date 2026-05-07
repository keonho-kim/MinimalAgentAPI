from minial_agent.constants.display import DisplayInfo


AGENT_DISPLAY_MAP: dict[str, DisplayInfo] = {
    "office_file_agent": DisplayInfo(
        label="오피스 파일 에이전트",
        running_message="AGENT가 오피스 파일 작업을 위임합니다.",
        completed_message="AGENT가 오피스 파일 작업을 완료했습니다.",
        error_message="AGENT가 오피스 파일 작업 중 오류가 발생했습니다.",
        pending_message="AGENT가 오피스 파일 작업을 준비합니다.",
    ),
    "agent_pdf": DisplayInfo(
        label="PDF 에이전트",
        running_message="AGENT가 PDF 분석을 시작합니다.",
        completed_message="AGENT가 PDF 분석을 완료했습니다.",
        error_message="AGENT가 PDF 분석 중 오류가 발생했습니다.",
        pending_message="AGENT가 PDF 분석을 준비합니다.",
    ),
    "agent_docx": DisplayInfo(
        label="DOCX 에이전트",
        running_message="AGENT가 DOCX 작업을 시작합니다.",
        completed_message="AGENT가 DOCX 작업을 완료했습니다.",
        error_message="AGENT가 DOCX 작업 중 오류가 발생했습니다.",
        pending_message="AGENT가 DOCX 작업을 준비합니다.",
    ),
    "agent_hwpx": DisplayInfo(
        label="HWPX 에이전트",
        running_message="AGENT가 HWPX 작업을 시작합니다.",
        completed_message="AGENT가 HWPX 작업을 완료했습니다.",
        error_message="AGENT가 HWPX 작업 중 오류가 발생했습니다.",
        pending_message="AGENT가 HWPX 작업을 준비합니다.",
    ),
    "agent_pptx": DisplayInfo(
        label="PPTX 에이전트",
        running_message="AGENT가 PPTX 작업을 시작합니다.",
        completed_message="AGENT가 PPTX 작업을 완료했습니다.",
        error_message="AGENT가 PPTX 작업 중 오류가 발생했습니다.",
        pending_message="AGENT가 PPTX 작업을 준비합니다.",
    ),
    "agent_xlsx": DisplayInfo(
        label="XLSX 에이전트",
        running_message="AGENT가 XLSX 작업을 시작합니다.",
        completed_message="AGENT가 XLSX 작업을 완료했습니다.",
        error_message="AGENT가 XLSX 작업 중 오류가 발생했습니다.",
        pending_message="AGENT가 XLSX 작업을 준비합니다.",
    ),
}


def is_agent_name(name: str | None) -> bool:
    return bool(name) and (
        name in AGENT_DISPLAY_MAP
        or name == "task"
        or "subagent" in name.lower()
        or name.startswith("agent_")
    )


def get_agent_display(name: str | None) -> DisplayInfo | None:
    if not name:
        return None
    return AGENT_DISPLAY_MAP.get(name)


def get_agent_label(name: str | None) -> str | None:
    display = get_agent_display(name)
    return display.label if display else None


def get_agent_message(name: str | None, status: str) -> str | None:
    display = get_agent_display(name)
    if not display:
        return None
    if status == "running":
        return display.running_message
    if status == "completed":
        return display.completed_message
    if status == "error":
        return display.error_message
    return display.pending_message
