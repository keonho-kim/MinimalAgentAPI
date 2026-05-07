from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayInfo:
    label: str
    running_message: str
    completed_message: str
    error_message: str
    pending_message: str


def standard_display(label: str) -> DisplayInfo:
    return DisplayInfo(
        label=label,
        running_message=f"AGENT가 {label} 작업을 시작합니다.",
        completed_message=f"AGENT가 {label} 작업을 완료했습니다.",
        error_message=f"AGENT가 {label} 작업 중 오류가 발생했습니다.",
        pending_message=f"AGENT가 {label} 작업을 준비합니다.",
    )
