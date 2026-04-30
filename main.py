from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from minial_agent.api.agent.router import router as agent_router
from minial_agent.api.fs.router import router as fs_router
from minial_agent.api.processor.router import router as processor_router
from minial_agent.common.config.loader import set_config

set_config("env.toml")

STATIC_DIR = Path(__file__).resolve().parent / "src" / "static"

app = FastAPI(title="MinimalAgent API")
app.include_router(agent_router)
app.include_router(fs_router)
app.include_router(processor_router)


@app.get("/ui", include_in_schema=False)
async def static_ui_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
