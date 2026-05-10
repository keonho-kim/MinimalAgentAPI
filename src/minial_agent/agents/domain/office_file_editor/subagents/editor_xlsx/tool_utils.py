import json


def json_result(value: dict | list) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
