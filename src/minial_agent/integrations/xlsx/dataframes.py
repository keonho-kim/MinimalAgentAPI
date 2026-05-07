import json
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from minial_agent.integrations.xlsx.models import DataFrameProfile


def save_dataframe(path: Path, dataframe: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        dataframe.to_json(orient="split", date_format="iso", force_ascii=False),
        encoding="utf-8",
    )


def load_dataframe(path: Path) -> pd.DataFrame:
    return pd.read_json(StringIO(path.read_text(encoding="utf-8")), orient="split")


def preview_dataframe(dataframe: pd.DataFrame, *, max_rows: int = 20) -> list[dict[str, Any]]:
    limited = dataframe.head(max(max_rows, 0))
    return _records(limited)


def profile_dataframe(name: str, dataframe: pd.DataFrame) -> DataFrameProfile:
    numeric_stats: dict[str, dict[str, float | int | None]] = {}
    numeric = dataframe.select_dtypes(include="number")
    for column in numeric.columns:
        series = numeric[column].dropna()
        numeric_stats[str(column)] = {
            "count": int(series.count()),
            "mean": _float_or_none(series.mean()),
            "min": _float_or_none(series.min()),
            "max": _float_or_none(series.max()),
            "sum": _float_or_none(series.sum()),
        }

    categorical_top_values: dict[str, list[dict[str, Any]]] = {}
    for column in dataframe.columns:
        if str(column) in numeric_stats:
            continue
        counts = dataframe[column].dropna().astype(str).value_counts().head(5)
        categorical_top_values[str(column)] = [
            {"value": str(index), "count": int(count)}
            for index, count in counts.items()
        ]

    return DataFrameProfile(
        name=name,
        shape=(int(dataframe.shape[0]), int(dataframe.shape[1])),
        columns=[str(column) for column in dataframe.columns],
        dtypes={str(column): str(dtype) for column, dtype in dataframe.dtypes.items()},
        null_counts={str(column): int(count) for column, count in dataframe.isna().sum().items()},
        numeric_stats=numeric_stats,
        categorical_top_values=categorical_top_values,
        sample_rows=preview_dataframe(dataframe, max_rows=10),
    )


def dataframe_to_matrix(dataframe: pd.DataFrame, *, include_header: bool = True) -> list[list[Any]]:
    matrix: list[list[Any]] = []
    if include_header:
        matrix.append([str(column) for column in dataframe.columns])
    matrix.extend(dataframe.where(pd.notna(dataframe), None).values.tolist())
    return _json_matrix(matrix)


def _records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    payload = dataframe.where(pd.notna(dataframe), None).to_dict(orient="records")
    return json.loads(json.dumps(payload, default=str, ensure_ascii=False))


def _json_matrix(values: list[list[Any]]) -> list[list[Any]]:
    return json.loads(json.dumps(values, default=str, ensure_ascii=False))


def _float_or_none(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
