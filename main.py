from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from minial_agent.api.endpoints.router import router
from minial_agent.common.config.loader import set_config

set_config("env.toml")

STATIC_DIR = Path(__file__).resolve().parent / "src" / "static"

app = FastAPI(title="MinimalAgent API")
app.include_router(router)


@app.get("/ui", include_in_schema=False)
async def static_ui_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
