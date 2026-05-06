from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from minial_agent.api.agent.router import router as agent_router
from minial_agent.api.fs.router import router as fs_router
from minial_agent.api.processor.router import router as processor_router
from minial_agent.api.session.router import router as session_router
from minial_agent.api.skills.router import router as skills_router
from minial_agent.common.config.loader import set_config

set_config("env.toml")

UI_DIST_DIR = Path(__file__).resolve().parent / "ui" / "dist"


def create_app(ui_dist_dir: Path = UI_DIST_DIR) -> FastAPI:
    app = FastAPI(title="MinimalAgent API")
    app.include_router(agent_router)
    app.include_router(fs_router)
    app.include_router(processor_router)
    app.include_router(session_router)
    app.include_router(skills_router)

    @app.get("/", include_in_schema=False)
    async def redirect_to_ui():
        return RedirectResponse(url="/ui")

    @app.get("/ui", include_in_schema=False)
    async def static_ui_index():
        index_path = ui_dist_dir / "index.html"
        if not index_path.is_file():
            return PlainTextResponse(
                "Frontend build not found. Run `bun run build` in ui first.",
                status_code=503,
            )
        return FileResponse(index_path)

    app.mount(
        "/ui",
        StaticFiles(directory=ui_dist_dir, html=True, check_dir=False),
        name="ui",
    )
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
