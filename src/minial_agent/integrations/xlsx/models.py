from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SheetInspection:
    sheet_name: str
    index: int
    visible: bool
    used_range: str
    row_count: int
    column_count: int
    headers: list[str] = field(default_factory=list)
    sample_rows: list[list[Any]] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    formula_count: int = 0
    tables: list[dict[str, Any]] = field(default_factory=list)
    chart_count: int = 0
    merged_ranges: list[str] = field(default_factory=list)
    candidate_ranges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "index": self.index,
            "visible": self.visible,
            "used_range": self.used_range,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "headers": self.headers,
            "sample_rows": self.sample_rows,
            "formulas": self.formulas,
            "formula_count": self.formula_count,
            "has_formulas": self.formula_count > 0,
            "tables": self.tables,
            "has_tables": bool(self.tables),
            "chart_count": self.chart_count,
            "has_charts": self.chart_count > 0,
            "merged_ranges": self.merged_ranges,
            "candidate_ranges": self.candidate_ranges,
        }


@dataclass(frozen=True)
class WorkbookInspection:
    filename: str
    sheet_count: int
    sheets: list[SheetInspection]

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "sheet_count": self.sheet_count,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
        }


@dataclass(frozen=True)
class RangeReadResult:
    sheet_name: str
    range: str
    headers: list[str]
    rows: list[dict[str, Any]]
    values: list[list[Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "range": self.range,
            "headers": self.headers,
            "rows": self.rows,
            "values": self.values,
            "column_count": len(self.headers),
            "row_count": len(self.rows),
            "value_row_count": len(self.values),
        }


@dataclass(frozen=True)
class DataFrameProfile:
    name: str
    shape: tuple[int, int]
    columns: list[str]
    dtypes: dict[str, str]
    null_counts: dict[str, int]
    numeric_stats: dict[str, dict[str, float | int | None]]
    categorical_top_values: dict[str, list[dict[str, Any]]]
    sample_rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "shape": list(self.shape),
            "columns": self.columns,
            "dtypes": self.dtypes,
            "null_counts": self.null_counts,
            "numeric_stats": self.numeric_stats,
            "categorical_top_values": self.categorical_top_values,
            "sample_rows": self.sample_rows,
        }


@dataclass(frozen=True)
class SessionChange:
    action: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "details": self.details}


@dataclass(frozen=True)
class SessionManifest:
    session_id: str
    source_file_id: str
    source_filename: str
    instruction: str
    working_filename: str = "working.xlsx"
    dataframes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_file_id": self.source_file_id,
            "source_filename": self.source_filename,
            "instruction": self.instruction,
            "working_filename": self.working_filename,
            "dataframes": self.dataframes,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SessionManifest":
        return cls(
            session_id=str(value["session_id"]),
            source_file_id=str(value["source_file_id"]),
            source_filename=str(value["source_filename"]),
            instruction=str(value.get("instruction", "")),
            working_filename=str(value.get("working_filename", "working.xlsx")),
            dataframes=[str(item) for item in value.get("dataframes", [])],
        )
