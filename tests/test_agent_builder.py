from minial_agent.agents.core import agent_builder
from minial_agent.agents.core.agent_builder import AgentBuilder
import pytest


def test_agent_builder_uses_files_workspace(tmp_path, monkeypatch) -> None:
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    def fake_summarization_middleware(**kwargs):
        return {"summarization": kwargs}

    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(agent_builder, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_builder,
        "SummarizationMiddleware",
        fake_summarization_middleware,
    )
    monkeypatch.setattr(AgentBuilder, "_get_llm", lambda self: "fake-model")

    AgentBuilder().get_agent(user_id="user", uuid="session")

    workspace = tmp_path / "user"
    assert workspace.is_dir()
    assert (workspace / "files").is_dir()
    assert (workspace / ".outputs").is_dir()
    assert (workspace / ".registry" / "files.json").is_file()
    assert (workspace / ".converted").is_dir()
    assert captured["model"] == "fake-model"


def test_agent_builder_uses_same_workspace_for_user_sessions(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))

    builder = AgentBuilder()

    assert builder._get_workspace_root(user_id="user", uuid="one") == str(
        tmp_path / "user" / "files"
    )
    assert builder._get_workspace_root(user_id="user", uuid="two") == str(
        tmp_path / "user" / "files"
    )


def test_agent_builder_rejects_nested_workspace_parts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))

    with pytest.raises(ValueError):
        AgentBuilder()._get_workspace_root(user_id="../user", uuid="session")
