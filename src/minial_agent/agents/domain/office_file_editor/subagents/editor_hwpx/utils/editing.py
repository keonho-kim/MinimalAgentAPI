import zipfile
from pathlib import Path
from typing import Any, Callable
from xml.sax.saxutils import escape


def apply_hwpx_edit(
    *,
    path: Path,
    operation: str,
    slots: dict[str, str],
    source_filename: str,
) -> list[dict[str, Any]]:
    if operation == "replace_text":
        old_text = slots.get("OLD_TEXT")
        new_value = slots.get("NEW_TEXT")
        if old_text is None or new_value is None:
            raise ValueError("HWPX replace_text requires OLD_TEXT and NEW_TEXT.")
        changed_count = _rewrite_hwpx_xml(
            path,
            lambda text: text.replace(old_text, new_value),
        )
    elif operation == "add_paragraph":
        new_value = slots.get("TEXT")
        if new_value is None:
            raise ValueError("HWPX add_paragraph requires TEXT.")
        paragraph = f"<hp:p><hp:run><hp:t>{escape(new_value)}</hp:t></hp:run></hp:p>"
        changed_count = _rewrite_hwpx_xml(
            path,
            lambda text: text.replace("</hp:body>", f"{paragraph}</hp:body>"),
        )
    else:
        raise ValueError(f"Unsupported HWPX edit operation: {operation}")
    if changed_count == 0:
        raise ValueError("HWPX edit did not change the document.")
    return [
        {
            "source_file": source_filename,
            "operation": operation,
            "new_value": new_value,
            "changed_count": changed_count,
        }
    ]


def _rewrite_hwpx_xml(path: Path, rewrite: Callable[[str], str]) -> int:
    try:
        with zipfile.ZipFile(path, "r") as source:
            items = [(item, source.read(item.filename)) for item in source.infolist()]
    except zipfile.BadZipFile as exc:
        raise ValueError("HWPX file is not a valid zip package.") from exc

    changed_count = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for item, data in items:
            if item.filename.endswith(".xml"):
                text = data.decode("utf-8", errors="ignore")
                rewritten = rewrite(text)
                if rewritten != text:
                    changed_count += 1
                data = rewritten.encode("utf-8")
            target.writestr(item, data)
    return changed_count
