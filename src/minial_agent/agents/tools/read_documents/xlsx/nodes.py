import re

from minial_agent.common.utils.file_registry import resolve_artifact
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact
from minial_agent.integrations.xlsx.dataframes import profile_dataframe, preview_dataframe
from minial_agent.integrations.xlsx.ranges import range_to_dataframe, read_range
from minial_agent.integrations.xlsx.workbook import inspect_workbook as inspect_xlsx_workbook


def resolve_xlsx_artifact(
    workspace: UploadWorkspace,
    file_ref: str,
) -> ResolvedUploadArtifact:
    return resolve_artifact(
        workspace=workspace,
        file_ref=file_ref,
        expected_file_type="xlsx",
    )


def inspect_workbook(artifact: ResolvedUploadArtifact) -> dict:
    inspection = inspect_xlsx_workbook(
        artifact.source_path,
        filename=artifact.visible_name,
    ).to_dict()
    inspection.update(
        {
        "file_id": artifact.file_id,
        "filename": artifact.visible_name,
        }
    )
    return inspection


def read_question_range(artifact: ResolvedUploadArtifact, *, question: str, workbook: dict) -> dict:
    selection = _select_range(question=question, workbook=workbook)
    if not selection:
        return {}
    range_result = read_range(
        artifact.source_path,
        selection["sheet"],
        selection["range"],
        header=True,
    )
    dataframe = range_to_dataframe(
        artifact.source_path,
        selection["sheet"],
        selection["range"],
        header=True,
    )
    return {
        "range": range_result.to_dict(),
        "profile": profile_dataframe("selected_range", dataframe).to_dict(),
        "preview": preview_dataframe(dataframe),
    }


def answer_xlsx(*, artifact: ResolvedUploadArtifact, question: str) -> dict:
    workbook = inspect_workbook(artifact)
    selected = read_question_range(artifact, question=question, workbook=workbook)
    result = {
        "file_id": artifact.file_id,
        "filename": artifact.visible_name,
        "question": question,
        "workbook": workbook,
        "selected_range": selected,
        "guidance": (
            "Use the XLSX editor subagent session tools for calculations, dataframe "
            "transforms, workbook edits, formulas, or export tasks."
        ),
    }
    return result


def _select_range(*, question: str, workbook: dict) -> dict[str, str] | None:
    match = re.search(r"\b([A-Z]{1,3}\d{1,7}\s*:\s*[A-Z]{1,3}\d{1,7})\b", question, re.IGNORECASE)
    if not match:
        return None
    range_ref = match.group(1).replace(" ", "").upper()
    sheets = workbook.get("sheets", [])
    sheet_name = _mentioned_sheet(question, sheets)
    if not sheet_name and len(sheets) == 1:
        sheet_name = str(sheets[0].get("sheet_name", ""))
    if not sheet_name:
        raise ValueError("A sheet name is required when a workbook has multiple sheets.")
    return {"sheet": sheet_name, "range": range_ref}


def _mentioned_sheet(question: str, sheets: list[dict]) -> str | None:
    lowered = question.lower()
    for sheet in sheets:
        name = str(sheet.get("sheet_name", ""))
        if name and name.lower() in lowered:
            return name
    quoted = re.search(r"'([^']+)'!\s*[A-Z]{1,3}\d{1,7}", question, re.IGNORECASE)
    if quoted:
        return quoted.group(1)
    return None
