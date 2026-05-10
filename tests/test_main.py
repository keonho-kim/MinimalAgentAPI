import importlib.util
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.common.config.loader import set_config


def load_root_main(monkeypatch, config_file: Path):
    monkeypatch.setenv("MINIAL_AGENT_BACKEND_CONFIG", str(config_file))
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("root_main", main_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_backend_config(tmp_path, *, mount_ui: bool = True) -> Path:
    config_file = tmp_path / "env.backend.toml"
    workspace = tmp_path / "workspace"
    config_file.write_text(
        f"""
[serving]
mount_ui={str(mount_ui).lower()}

[fs]
workspace="{workspace}"

[llm]
provider="openai-compatible"
base_url="http://127.0.0.1:1234"
model_name="test-model"
api_key="EMPTY"
max_tokens=128
tls_verify=false
""".strip(),
        encoding="utf-8",
    )
    return config_file


def test_root_main_exposes_fastapi_app(tmp_path, monkeypatch) -> None:
    module = load_root_main(monkeypatch, write_backend_config(tmp_path))

    assert isinstance(module.app, FastAPI)


def test_root_main_redirects_root_to_ui(tmp_path, monkeypatch) -> None:
    module = load_root_main(monkeypatch, write_backend_config(tmp_path))
    client = TestClient(module.create_app())

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_root_main_mounts_built_ui_dist(tmp_path, monkeypatch) -> None:
    module = load_root_main(monkeypatch, write_backend_config(tmp_path))
    ui_dist = tmp_path / "dist"
    assets_dir = ui_dist / "assets"
    assets_dir.mkdir(parents=True)
    (ui_dist / "index.html").write_text(
        '<div id="root"></div><script type="module" src="/ui/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text(
        'document.querySelector("#root").textContent = "MinimalAgent";',
        encoding="utf-8",
    )

    client = TestClient(module.create_app(ui_dist_dir=ui_dist))

    index_response = client.get("/ui")
    script_response = client.get("/ui/assets/app.js")

    assert index_response.status_code == 200
    assert "/ui/assets/app.js" in index_response.text
    assert index_response.headers["cache-control"] == "no-store"
    assert script_response.status_code == 200
    assert "MinimalAgent" in script_response.text


def test_root_main_reports_missing_frontend_build(tmp_path, monkeypatch) -> None:
    module = load_root_main(monkeypatch, write_backend_config(tmp_path))
    client = TestClient(module.create_app(ui_dist_dir=tmp_path / "missing-dist"))

    response = client.get("/ui")

    assert response.status_code == 503
    assert "Frontend build not found" in response.text


def test_root_main_can_disable_ui_mount(tmp_path, monkeypatch) -> None:
    module = load_root_main(
        monkeypatch,
        write_backend_config(tmp_path, mount_ui=False),
    )
    client = TestClient(module.app)

    root_response = client.get("/", follow_redirects=False)
    ui_response = client.get("/ui")

    assert root_response.status_code == 404
    assert ui_response.status_code == 404


def test_backend_sample_config_loads(monkeypatch) -> None:
    monkeypatch.delenv("MINIAL_AGENT_MOUNT_UI", raising=False)
    monkeypatch.delenv("VLM_MAX_CONCURRENCY", raising=False)

    set_config("env.backend.toml.sample")

    assert os.environ["MINIAL_AGENT_MOUNT_UI"] == "true"
    assert os.environ["VLM_MAX_CONCURRENCY"] == "20"
