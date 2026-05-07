import csv
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook

from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact
from minial_agent.integrations.upload.storage import unique_path
from minial_agent.integrations.xlsx.dataframes import dataframe_to_matrix
from minial_agent.integrations.xlsx.detect_tables import detect_table
from minial_agent.integrations.xlsx.ranges import read_range
from minial_agent.integrations.xlsx.references import resolve_output_filename, resolve_output_path


def export_range(
    *,
    workspace: UploadWorkspace,
    source_artifact: ResolvedUploadArtifact,
    workbook_path: Path,
    sheet: str,
    range_ref: str,
    output_path: str,
) -> dict[str, Any]:
    requested_target = resolve_output_path(workspace, output_path, allowed_extensions={".xlsx", ".csv"})
    result = read_range(workbook_path, sheet, range_ref, header=False)
    if requested_target.suffix.lower() == ".csv":
        target = _unique_output(requested_target)
        _write_csv(target, result.values)
        return _csv_result(
            workspace=workspace,
            path=target,
            row_count=len(result.values),
            column_count=len(result.values[0]) if result.values else 0,
        )
    target = _temp_output(workspace, requested_target.name)
    _write_xlsx(target, result.values, sheet_name=result.sheet_name)
    registered = _register_xlsx(
        workspace=workspace,
        source_artifact=source_artifact,
        output_path=target,
        changed_items=[
            {
                "action": "export_range",
                "sheet": result.sheet_name,
                "range": result.range,
                "row_count": len(result.values),
            }
        ],
    )
    return registered


def export_dataframe(
    *,
    workspace: UploadWorkspace,
    source_artifact: ResolvedUploadArtifact,
    dataframe: pd.DataFrame,
    output_path: str,
) -> dict[str, Any]:
    requested_target = resolve_output_path(workspace, output_path, allowed_extensions={".xlsx", ".csv"})
    matrix = dataframe_to_matrix(dataframe, include_header=True)
    if requested_target.suffix.lower() == ".csv":
        target = _unique_output(requested_target)
        _write_csv(target, matrix)
        return _csv_result(
            workspace=workspace,
            path=target,
            row_count=len(matrix),
            column_count=len(matrix[0]) if matrix else 0,
        )
    target = _temp_output(workspace, requested_target.name)
    _write_xlsx(target, matrix, sheet_name="Data")
    return _register_xlsx(
        workspace=workspace,
        source_artifact=source_artifact,
        output_path=target,
        changed_items=[
            {
                "action": "export_dataframe",
                "row_count": len(dataframe),
                "column_count": len(dataframe.columns),
            }
        ],
    )


def export_detected_table_csv(
    *,
    workspace: UploadWorkspace,
    workbook_path: Path,
    output_filename: str,
    sheet: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    table = detect_table(workbook_path, sheet=sheet)
    result = read_range(workbook_path, table.sheet, table.range, header=False)
    target = _csv_target(
        workspace=workspace,
        output_filename=output_filename,
        overwrite=overwrite,
    )
    overwritten = target.exists()
    _write_csv(target, result.values)
    return _csv_result(
        workspace=workspace,
        path=target,
        row_count=table.row_count + 1,
        column_count=table.column_count,
        overwritten=overwritten,
        detected_range=table.to_dict(),
    )


def export_dataframe_csv(
    *,
    workspace: UploadWorkspace,
    dataframe: pd.DataFrame,
    output_filename: str,
    overwrite: bool = True,
) -> dict[str, Any]:
    target = _csv_target(
        workspace=workspace,
        output_filename=output_filename,
        overwrite=overwrite,
    )
    overwritten = target.exists()
    matrix = dataframe_to_matrix(dataframe, include_header=True)
    _write_csv(target, matrix)
    return _csv_result(
        workspace=workspace,
        path=target,
        row_count=len(matrix),
        column_count=len(matrix[0]) if matrix else 0,
        overwritten=overwritten,
        detected_range=None,
    )


def commit_workbook(
    *,
    workspace: UploadWorkspace,
    source_artifact: ResolvedUploadArtifact,
    workbook_path: Path,
    output_path: str,
    summary: str,
    changed_items: list[dict[str, Any]],
) -> dict[str, Any]:
    requested_target = resolve_output_path(workspace, output_path, allowed_extensions={".xlsx"})
    target = _temp_output(workspace, requested_target.name)
    shutil.copyfile(workbook_path, target)
    return _register_xlsx(
        workspace=workspace,
        source_artifact=source_artifact,
        output_path=target,
        changed_items=[*changed_items, {"action": "commit_session", "summary": summary}],
    )


def _register_xlsx(
    *,
    workspace: UploadWorkspace,
    source_artifact: ResolvedUploadArtifact,
    output_path: Path,
    changed_items: list[dict[str, Any]],
) -> dict[str, Any]:
    edited_file, _manifest = file_registry.register_edited_file(
        workspace=workspace,
        source_artifact=source_artifact,
        edited_path=output_path,
        changed_items=changed_items,
    )
    return {
        "summary": f"{edited_file.filename} 파일을 생성했습니다.",
        "file": {
            "file_id": edited_file.file_id,
            "filename": edited_file.filename,
            "download_url": edited_file.download_url,
        },
        "changed_items": changed_items,
    }


def _write_xlsx(path: Path, values: list[list[Any]], *, sheet_name: str) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = (sheet_name or "Sheet1")[:31]
    for row_index, row in enumerate(values, start=1):
        for column_index, value in enumerate(row, start=1):
            worksheet.cell(row=row_index, column=column_index).value = value
    workbook.save(path)
    workbook.close()


def _write_csv(path: Path, values: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(values)


def _csv_result(
    *,
    workspace: UploadWorkspace,
    path: Path,
    row_count: int,
    column_count: int,
    overwritten: bool = False,
    detected_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "summary": f"{path.name} CSV 파일을 생성했습니다.",
        "file": {
            "filename": path.name,
            "visible_path": "/" + path.resolve().relative_to(workspace.files_dir.resolve()).as_posix(),
        },
        "row_count": row_count,
        "column_count": column_count,
        "overwritten": overwritten,
    }
    if detected_range is not None:
        result["detected_range"] = detected_range
    return result


def _unique_output(path: Path) -> Path:
    return unique_path(path)


def _temp_output(workspace: UploadWorkspace, filename: str) -> Path:
    export_dir = workspace.cache_dir / "xlsx_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(export_dir / filename)


def _csv_target(
    *,
    workspace: UploadWorkspace,
    output_filename: str,
    overwrite: bool,
) -> Path:
    target = resolve_output_filename(
        workspace,
        output_filename,
        extension=".csv",
    )
    return target if overwrite else _unique_output(target)
