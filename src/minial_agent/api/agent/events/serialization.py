from typing import Any

from fastapi.encoders import jsonable_encoder


def object_or_empty(value: Any) -> dict[str, Any]:
    value = jsonable_mapping(value)
    return value if isinstance(value, dict) else {}


def jsonable_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: jsonable_mapping(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable_mapping(item) for item in value]
    if isinstance(value, tuple):
        return [jsonable_mapping(item) for item in value]

    try:
        return jsonable_encoder(value)
    except Exception:
        return value
