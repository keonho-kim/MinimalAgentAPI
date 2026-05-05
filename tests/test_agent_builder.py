import pytest
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from minial_agent.agents.core import agent_builder
from minial_agent.agents.core.agent_builder import AgentBuilder
from minial_agent.agents.domain.office_file_agent import agent as office_agent


def test_agent_builder_uses_files_workspace(tmp_path, monkeypatch) -> None:
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    def fake_summarization_middleware(**kwargs):
        return {"summarization": kwargs}

    def fake_filesystem_middleware(**kwargs):
        return {"filesystem": kwargs}

    def fake_subagent_middleware(**kwargs):
        return {"subagents": kwargs}

    def fake_patch_tool_calls_middleware():
        return {"patch_tool_calls": True}

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(agent_builder, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_builder,
        "build_office_file_agent",
        lambda **kwargs: {"office_agent": kwargs},
    )
    monkeypatch.setattr(
        agent_builder,
        "FilesystemMiddleware",
        fake_filesystem_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "SubAgentMiddleware",
        fake_subagent_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "SummarizationMiddleware",
        fake_summarization_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "HumanInTheLoopMiddleware",
        fake_hitl_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "PatchToolCallsMiddleware",
        fake_patch_tool_calls_middleware,
    )
    llm_calls = []

    def fake_llm_client(*, disable_streaming=False):
        llm_calls.append(disable_streaming)
        return f"fake-model:{disable_streaming}"

    monkeypatch.setattr(agent_builder, "llm_client", fake_llm_client)

    AgentBuilder().get_agent(user_id="user", uuid="session")

    workspace = tmp_path / "user"
    assert workspace.is_dir()
    assert (workspace / "files").is_dir()
    assert (workspace / ".outputs").is_dir()
    assert (workspace / ".registry" / "files.json").is_file()
    assert (workspace / ".converted").is_dir()
    assert captured["model"] == "fake-model:False"
    backend = captured["middleware"][0]["filesystem"]["backend"]
    assert captured["middleware"][1]["subagents"]["backend"] is backend
    assert captured["middleware"][1]["subagents"]["subagents"][0]["name"] == (
        "office_file_agent"
    )
    assert captured["middleware"][1]["subagents"]["subagents"][0]["runnable"][
        "office_agent"
    ]["backend"] is backend
    assert captured["middleware"][1]["subagents"]["subagents"][0]["runnable"][
        "office_agent"
    ]["checkpointer"] is captured["checkpointer"]
    assert captured["middleware"][2]["summarization"]["model"] == "fake-model:False"
    assert set(captured["middleware"][3]["hitl"]["interrupt_on"]) == {
        "write_file",
        "edit_file",
    }
    assert captured["middleware"][3]["hitl"]["interrupt_on"]["write_file"][
        "allowed_decisions"
    ] == ["approve", "edit", "reject"]
    assert captured["middleware"][4]["patch_tool_calls"] is True
    assert captured["checkpointer"] is not None
    assert captured["store"] is not None
    assert backend.cwd == workspace / "files"
    assert llm_calls == [False, False]


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


def test_office_file_agent_uses_create_agent_with_worker_subagents(monkeypatch) -> None:
    captured_calls = []

    def fake_create_agent(**kwargs):
        captured_calls.append(kwargs)
        return {"agent": kwargs}

    def fake_filesystem_middleware(**kwargs):
        return {"filesystem": kwargs}

    def fake_subagent_middleware(**kwargs):
        return {"subagents": kwargs}

    def fake_patch_tool_calls_middleware():
        return {"patch_tool_calls": True}

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setattr(office_agent, "create_agent", fake_create_agent)
    monkeypatch.setattr(office_agent, "FilesystemMiddleware", fake_filesystem_middleware)
    monkeypatch.setattr(office_agent, "SubAgentMiddleware", fake_subagent_middleware)
    monkeypatch.setattr(office_agent, "HumanInTheLoopMiddleware", fake_hitl_middleware)
    monkeypatch.setattr(
        office_agent,
        "PatchToolCallsMiddleware",
        fake_patch_tool_calls_middleware,
    )

    model = FakeListChatModel(responses=["ok"])
    backend = FilesystemBackend(
        root_dir="/tmp/minial-office-test",
        virtual_mode=True,
        max_file_size_mb=1024,
    )

    office_agent.build_office_file_agent(
        model=model,
        backend=backend,
        store=None,
        checkpointer="shared-checkpointer",
    )

    worker_calls = captured_calls[:5]
    captured = captured_calls[5]
    assert captured["model"] is model
    assert captured["checkpointer"] == "shared-checkpointer"
    assert captured["middleware"][0]["filesystem"]["backend"] is backend
    assert captured["middleware"][1]["subagents"]["backend"] is backend
    subagents = captured["middleware"][1]["subagents"]["subagents"]
    assert [subagent["name"] for subagent in subagents] == [
        "agent_hwpx",
        "agent_docx",
        "agent_pptx",
        "agent_xlsx",
        "agent_pdf",
    ]
    assert all("runnable" in subagent for subagent in subagents)
    assert [call["name"] for call in worker_calls] == [
        "agent_hwpx",
        "agent_docx",
        "agent_pptx",
        "agent_xlsx",
        "agent_pdf",
    ]
    assert all(call["model"] is model for call in worker_calls)
    assert all(call["checkpointer"] == "shared-checkpointer" for call in worker_calls)
    assert all(call["store"] is None for call in worker_calls)
    assert all(call["middleware"][0]["filesystem"]["backend"] is backend for call in worker_calls)
    assert set(captured["middleware"][2]["hitl"]["interrupt_on"]) == {
        "write_file",
        "edit_file",
    }
    assert captured["middleware"][3]["patch_tool_calls"] is True
    worker_hitl = {
        call["name"]: set(call["middleware"][1]["hitl"]["interrupt_on"])
        for call in worker_calls
    }
    assert worker_hitl["agent_docx"] == {"write_file", "edit_file", "edit_docx"}
    assert worker_hitl["agent_hwpx"] == {"write_file", "edit_file", "edit_hwpx"}
    assert worker_hitl["agent_pptx"] == {"write_file", "edit_file", "edit_pptx"}
    assert worker_hitl["agent_xlsx"] == {"write_file", "edit_file", "edit_xlsx"}
    assert worker_hitl["agent_pdf"] == {"write_file", "edit_file"}
