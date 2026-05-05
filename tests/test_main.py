import importlib.util
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


def test_root_main_redirects_root_to_ui() -> None:
    module = load_root_main()
    client = TestClient(module.create_app())

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_root_main_mounts_built_ui_dist(tmp_path) -> None:
    module = load_root_main()
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
    assert script_response.status_code == 200
    assert "MinimalAgent" in script_response.text


def test_root_main_reports_missing_frontend_build(tmp_path) -> None:
    module = load_root_main()
    client = TestClient(module.create_app(ui_dist_dir=tmp_path / "missing-dist"))

    response = client.get("/ui")

    assert response.status_code == 503
    assert "Frontend build not found" in response.text
