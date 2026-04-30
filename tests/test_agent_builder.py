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

    def fake_tool_selector_middleware(**kwargs):
        return {"tool_selector": kwargs}

    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(agent_builder, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_builder,
        "SummarizationMiddleware",
        fake_summarization_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "LLMToolSelectorMiddleware",
        fake_tool_selector_middleware,
    )
    llm_calls = []

    def fake_get_llm(self, *, disable_streaming=False):
        llm_calls.append(disable_streaming)
        return f"fake-model:{disable_streaming}"

    monkeypatch.setattr(AgentBuilder, "_get_llm", fake_get_llm)

    AgentBuilder().get_agent(user_id="user", uuid="session")

    workspace = tmp_path / "user"
    assert workspace.is_dir()
    assert (workspace / "files").is_dir()
    assert (workspace / ".outputs").is_dir()
    assert (workspace / ".registry" / "files.json").is_file()
    assert (workspace / ".converted").is_dir()
    assert captured["model"] == "fake-model:False"
    assert captured["middleware"][1]["summarization"]["model"] == "fake-model:False"
    assert captured["middleware"][2]["tool_selector"]["model"] == "fake-model:True"
    assert True in llm_calls


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
