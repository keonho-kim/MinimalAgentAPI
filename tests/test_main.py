import importlib.util
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def load_root_main():
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("root_main", main_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_root_main_exposes_fastapi_app() -> None:
    module = load_root_main()

    assert isinstance(module.app, FastAPI)


def test_root_main_mounts_static_ui() -> None:
    module = load_root_main()
    client = TestClient(module.app)

    index_response = client.get("/ui")
    script_response = client.get("/ui/scripts/app.mjs")
    events_response = client.get("/ui/scripts/events.mjs")
    css_response = client.get("/ui/css/markdown.css")
    activity_css_response = client.get("/ui/css/chat.css")
    vendor_response = client.get("/ui/vendor/katex/katex.min.js")

    assert index_response.status_code == 200
    assert "MinimalAgent" in index_response.text
    assert script_response.status_code == 200
    assert "openChatEventSource" in script_response.text
    assert events_response.status_code == 200
    assert "normalizeStreamEvent" in events_response.text
    assert css_response.status_code == 200
    assert activity_css_response.status_code == 200
    assert "activity-card" in activity_css_response.text
    assert vendor_response.status_code == 200


def test_static_ui_uses_local_assets_only() -> None:
    static_root = Path(__file__).resolve().parents[1] / "src" / "static"
    index = (static_root / "index.html").read_text()
    render = (static_root / "scripts" / "render.mjs").read_text()
    dom = (static_root / "scripts" / "dom.mjs").read_text()
    app = (static_root / "scripts" / "app.mjs").read_text()

    assert "https://" not in index
    assert "http://" not in index
    assert "renderAssistantContent" in render
    assert "DOMPurify.sanitize" in render
    assert "katex.renderToString" in render
    assert "Raw events" not in dom
    assert "appendRawEvent" not in app


def test_activity_payload_css_wraps_long_text() -> None:
    chat_css = (
        Path(__file__).resolve().parents[1] / "src" / "static" / "css" / "chat.css"
    ).read_text()

    assert ".activity-payload" in chat_css
    assert "white-space: pre-wrap" in chat_css
    assert "overflow-wrap: anywhere" in chat_css
    assert "max-height: 220px" in chat_css


def test_static_event_parser_smoke() -> None:
    if shutil.which("node") is None:
        return

    script = Path(__file__).resolve().parent / "static_event_smoke.mjs"
    subprocess.run(["node", str(script)], check=True)
