import pytest
from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from minial_agent.agents.core import agent_builder
from minial_agent.agents.core.agent_builder import AgentBuilder
from minial_agent.agents.core.system_prompt import CORE_AGENT_SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_agent import agent as office_agent
from minial_agent.agents.domain.office_file_agent.system_prompt import (
    OFFICE_FILE_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_docx.system_prompt import (
    DOCX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_hwpx.system_prompt import (
    HWPX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pdf.system_prompt import (
    PDF_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_pptx.system_prompt import (
    PPTX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_agent.subagents.agent_xlsx.system_prompt import (
    XLSX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.constants.user_request import USER_REQUEST


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

    def fake_tool_call_limit_middleware(**kwargs):
        return {"tool_call_limit": kwargs}

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(agent_builder, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_builder,
        "build_office_file_subagent",
        lambda **kwargs: {
            "name": "office_file_agent",
            "runnable": {"office_agent": kwargs},
        },
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
    assert (workspace / ".agents" / "skills").is_dir()
    assert captured["model"] == "fake-model:False"
    core_backend = captured["middleware"][0]["filesystem"]["backend"]
    assert isinstance(core_backend, CompositeBackend)
    skills_middleware = captured["middleware"][1]
    assert isinstance(skills_middleware, SkillsMiddleware)
    assert skills_middleware.sources == ["/.agents/skills"]
    assert skills_middleware.source_labels == ["Workspace"]
    files_backend = captured["middleware"][2]["subagents"]["backend"]
    assert core_backend.default is files_backend
    assert core_backend.routes["/.agents/"].cwd == workspace / ".agents"
    assert captured["middleware"][2]["subagents"]["subagents"][0]["name"] == (
        "office_file_agent"
    )
    assert captured["middleware"][2]["subagents"]["subagents"][0]["runnable"][
        "office_agent"
    ]["backend"] is files_backend
    assert captured["middleware"][2]["subagents"]["subagents"][0]["runnable"][
        "office_agent"
    ]["checkpointer"] is captured["checkpointer"]
    assert captured["middleware"][3]["summarization"]["model"] == "fake-model:False"
    assert set(captured["middleware"][4]["hitl"]["interrupt_on"]) == {
        "write_file",
        "edit_file",
    }
    assert captured["middleware"][4]["hitl"]["interrupt_on"]["write_file"][
        "allowed_decisions"
    ] == ["approve", "edit", "reject"]
    assert captured["middleware"][5]["patch_tool_calls"] is True
    assert captured["checkpointer"] is not None
    assert captured["store"] is not None
    assert files_backend.cwd == workspace / "files"
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


def test_agent_prompts_use_files_rooted_workspace_paths() -> None:
    prompts = [
        CORE_AGENT_SYSTEM_PROMPT,
        OFFICE_FILE_AGENT_SYSTEM_PROMPT,
        USER_REQUEST,
    ]

    assert all("/report.pdf" in prompt for prompt in prompts)
    assert all("never" in prompt and "files/" in prompt for prompt in prompts)


def test_agent_prompts_delegate_office_files_to_matching_subagents() -> None:
    assert "OfficeFile Domain Agent" in CORE_AGENT_SYSTEM_PROMPT
    assert "Do not read PDF or office binary files directly" in (
        CORE_AGENT_SYSTEM_PROMPT
    )
    assert "Delegate each supported office file request" in (
        OFFICE_FILE_AGENT_SYSTEM_PROMPT
    )
    assert "agent_pdf" in OFFICE_FILE_AGENT_SYSTEM_PROMPT
    assert "agent_docx" in OFFICE_FILE_AGENT_SYSTEM_PROMPT
    assert "agent_hwpx" in OFFICE_FILE_AGENT_SYSTEM_PROMPT
    assert "agent_pptx" in OFFICE_FILE_AGENT_SYSTEM_PROMPT
    assert "agent_xlsx" in OFFICE_FILE_AGENT_SYSTEM_PROMPT

    worker_prompts = [
        PDF_AGENT_SYSTEM_PROMPT,
        DOCX_AGENT_SYSTEM_PROMPT,
        HWPX_AGENT_SYSTEM_PROMPT,
        PPTX_AGENT_SYSTEM_PROMPT,
        XLSX_AGENT_SYSTEM_PROMPT,
    ]
    assert all("Do not use filesystem `read_file`" in prompt for prompt in worker_prompts)


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

    def fake_tool_call_limit_middleware(**kwargs):
        return {"tool_call_limit": kwargs}

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
    monkeypatch.setattr(
        office_agent,
        "ToolCallLimitMiddleware",
        fake_tool_call_limit_middleware,
    )

    model = FakeListChatModel(responses=["ok"])
    backend = FilesystemBackend(
        root_dir="/tmp/minial-office-test",
        virtual_mode=True,
        max_file_size_mb=1024,
    )

    office_subagent = office_agent.build_office_file_subagent(
        model=model,
        backend=backend,
        store=None,
        checkpointer="shared-checkpointer",
    )

    worker_calls = captured_calls[:5]
    captured = captured_calls[5]
    assert office_subagent["name"] == "office_file_agent"
    assert office_subagent["runnable"]["agent"] is captured
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
    assert all(
        call["middleware"][0]["filesystem"]["backend"] is backend
        for call in worker_calls
    )
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
    pdf_call = worker_calls[4]
    assert pdf_call["middleware"][2]["tool_call_limit"] == {
        "tool_name": "answer_pdf_question",
        "run_limit": 1,
        "exit_behavior": "continue",
    }
    assert pdf_call["middleware"][3]["patch_tool_calls"] is True
