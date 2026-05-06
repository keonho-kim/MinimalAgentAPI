# Minimal Agent

## Prerequisite

### Set UV venv

```bash 
uv venv .venv
uv sync
```

### Install Frontend Dependencies

```bash
cd ui
bun install
bun run build
```

## Start Server

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```
