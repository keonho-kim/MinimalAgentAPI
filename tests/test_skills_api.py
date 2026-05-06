from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.skills.router import router


def test_skill_search_returns_workspace_skills_without_os_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    skill_dir = tmp_path / "user" / ".agents" / "skills" / "writing-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: writing-guide
description: Use this skill when writing concise product copy.
---

# Writing Guide
""",
        encoding="utf-8",
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get(
        "/api/skills/search",
        params={"user_id": "user", "uuid": "session", "q": "copy"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "matches": [
            {
                "name": "writing-guide",
                "description": "Use this skill when writing concise product copy.",
                "path": "/.agents/skills/writing-guide/SKILL.md",
            }
        ]
    }
    assert str(tmp_path) not in response.text


def test_skill_search_allows_empty_query(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    for name in ("alpha", "beta"):
        skill_dir = tmp_path / "user" / ".agents" / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {name} skill.\n---\n",
            encoding="utf-8",
        )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get(
        "/api/skills/search",
        params={"user_id": "user", "uuid": "session", "q": "", "limit": "1"},
    )

    assert response.status_code == 200
    assert len(response.json()["matches"]) == 1
