import pytest
from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from minial_agent.agents.core import agent_builder
from minial_agent.agents.core.agent_builder import AgentBuilder
from minial_agent.agents.core.system_prompt import CORE_AGENT_SYSTEM_PROMPT
from minial_agent.agents.domain.office_file_editor import agent as office_agent
from minial_agent.agents.middleware import OfficeBinaryReadGuardMiddleware
from minial_agent.agents.domain.office_file_editor.subagents.editor_docx.system_prompt import (
    DOCX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_hwpx.system_prompt import (
    HWPX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_pptx.system_prompt import (
    PPTX_AGENT_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.system_prompt import (
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

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setenv("AGENT_RUNTIME_ROOT_DIR", str(tmp_path))
    monkeypatch.setattr(agent_builder, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_builder,
        "build_office_edit_subagents",
        lambda **kwargs: [
            {"name": "editor_docx", "runnable": {"edit_agent": kwargs}},
            {"name": "editor_xlsx", "runnable": {"edit_agent": kwargs}},
        ],
    )
    monkeypatch.setattr(
        agent_builder,
        "FilesystemMiddleware",
        fake_filesystem_middleware,
    )
    monkeypatch.setattr(
        agent_builder,
        "OfficeBinaryReadGuardMiddleware",
        lambda: {"office_binary_read_guard": True},
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
    assert captured["middleware"][1]["office_binary_read_guard"] is True
    skills_middleware = captured["middleware"][2]
    assert isinstance(skills_middleware, SkillsMiddleware)
    assert skills_middleware.sources == ["/.agents/skills"]
    assert skills_middleware.source_labels == ["Workspace"]
    files_backend = captured["middleware"][3]["subagents"]["backend"]
    assert core_backend.default is files_backend
    assert core_backend.routes["/.agents/"].cwd == workspace / ".agents"
    subagents = captured["middleware"][3]["subagents"]["subagents"]
    assert [subagent["name"] for subagent in subagents] == [
        "editor_docx",
        "editor_xlsx",
    ]
    assert all(
        subagent["runnable"]["edit_agent"]["backend"] is files_backend
        for subagent in subagents
    )
    assert all(
        subagent["runnable"]["edit_agent"]["checkpointer"] is captured["checkpointer"]
        for subagent in subagents
    )
    assert captured["middleware"][4]["summarization"]["model"] == "fake-model:False"
    assert set(captured["middleware"][5]["hitl"]["interrupt_on"]) == {
        "write_file",
        "edit_file",
        "rename_file",
        "move_file",
        "delete_file",
    }
    assert captured["middleware"][5]["hitl"]["interrupt_on"]["write_file"][
        "allowed_decisions"
    ] == ["approve", "edit", "reject"]
    assert captured["middleware"][6]["patch_tool_calls"] is True
    assert [tool.name for tool in captured["tools"]] == [
        "get_today",
        "rename_file",
        "move_file",
        "delete_file",
        "read_pdf_file",
        "read_docx_file",
        "read_hwpx_file",
        "read_pptx_file",
        "read_xlsx_file",
    ]
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
        USER_REQUEST,
    ]

    assert all("/report.pdf" in prompt for prompt in prompts)
    assert all("never" in prompt and "files/" in prompt for prompt in prompts)


def test_agent_prompts_use_core_read_tools_and_edit_subagents() -> None:
    assert "get_today" in CORE_AGENT_SYSTEM_PROMPT
    assert "read_pdf_file" in CORE_AGENT_SYSTEM_PROMPT
    assert "read_docx_file" in CORE_AGENT_SYSTEM_PROMPT
    assert "read_hwpx_file" in CORE_AGENT_SYSTEM_PROMPT
    assert "read_pptx_file" in CORE_AGENT_SYSTEM_PROMPT
    assert "read_xlsx_file" in CORE_AGENT_SYSTEM_PROMPT
    assert "full_scan=1" in CORE_AGENT_SYSTEM_PROMPT
    assert "full_scan=0" in CORE_AGENT_SYSTEM_PROMPT
    assert "matching edit subagent" in CORE_AGENT_SYSTEM_PROMPT
    assert "Do not read PDF or office binary files directly" in CORE_AGENT_SYSTEM_PROMPT

    worker_prompts = [
        DOCX_AGENT_SYSTEM_PROMPT,
        HWPX_AGENT_SYSTEM_PROMPT,
        PPTX_AGENT_SYSTEM_PROMPT,
        XLSX_AGENT_SYSTEM_PROMPT,
    ]
    assert all("<TOOLS>" in prompt for prompt in worker_prompts)
    assert all("get_today" in prompt for prompt in worker_prompts)
    assert "edit_docx" in DOCX_AGENT_SYSTEM_PROMPT
    assert "read_docx_file" in DOCX_AGENT_SYSTEM_PROMPT
    assert "edit_hwpx" in HWPX_AGENT_SYSTEM_PROMPT
    assert "read_hwpx_file" in HWPX_AGENT_SYSTEM_PROMPT
    assert "inspect_pptx_deck" in PPTX_AGENT_SYSTEM_PROMPT
    assert "edit_pptx" in PPTX_AGENT_SYSTEM_PROMPT
    assert "read_pptx_file" in PPTX_AGENT_SYSTEM_PROMPT
    assert "start_xlsx_session" in XLSX_AGENT_SYSTEM_PROMPT
    assert "commit_xlsx_session" in XLSX_AGENT_SYSTEM_PROMPT
    assert "read_xlsx_file" in XLSX_AGENT_SYSTEM_PROMPT


def test_office_edit_subagents_use_create_agent_with_edit_tools(monkeypatch) -> None:
    captured_calls = []

    def fake_create_agent(**kwargs):
        captured_calls.append(kwargs)
        return {"agent": kwargs}

    def fake_patch_tool_calls_middleware():
        return {"patch_tool_calls": True}

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setattr(office_agent, "create_agent", fake_create_agent)
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

    subagents = office_agent.build_office_edit_subagents(
        model=model,
        backend=backend,
        store=None,
        checkpointer="shared-checkpointer",
    )

    assert [subagent["name"] for subagent in subagents] == [
        "editor_hwpx",
        "editor_docx",
        "editor_pptx",
        "editor_xlsx",
    ]
    assert all("runnable" in subagent for subagent in subagents)
    assert [call["name"] for call in captured_calls] == [
        "editor_hwpx",
        "editor_docx",
        "editor_pptx",
        "editor_xlsx",
    ]
    assert all(call["model"] is model for call in captured_calls)
    assert all(
        call["checkpointer"] == "shared-checkpointer" for call in captured_calls
    )
    assert all(call["store"] is None for call in captured_calls)
    read_tool_names = [
        "get_today",
        "rename_file",
        "move_file",
        "delete_file",
        "read_pdf_file",
        "read_docx_file",
        "read_hwpx_file",
        "read_pptx_file",
        "read_xlsx_file",
    ]
    xlsx_tools = [
        "start_xlsx_session",
        "inspect_xlsx_session",
        "load_xlsx_range",
        "profile_xlsx_dataframe",
        "preview_xlsx_dataframe",
        "transform_xlsx_dataframe",
        "write_xlsx_dataframe",
        "write_xlsx_values",
        "add_xlsx_formula",
        "export_xlsx_range",
        "export_xlsx_dataframe",
        "export_xlsx_detected_table_csv",
        "export_xlsx_dataframe_csv",
        "commit_xlsx_session",
        "discard_xlsx_session",
    ]
    assert [[tool.name for tool in call["tools"]] for call in captured_calls] == [
        [*read_tool_names, "edit_hwpx"],
        [*read_tool_names, "edit_docx"],
        [*read_tool_names, "inspect_pptx_deck", "edit_pptx"],
        [*read_tool_names, *xlsx_tools],
    ]
    worker_hitl = {
        call["name"]: set(call["middleware"][0]["hitl"]["interrupt_on"])
        for call in captured_calls
    }
    assert worker_hitl["editor_docx"] == {"edit_docx"}
    assert worker_hitl["editor_hwpx"] == {"edit_hwpx"}
    assert worker_hitl["editor_pptx"] == {"edit_pptx"}
    assert worker_hitl["editor_xlsx"] == {
        "commit_xlsx_session",
        "export_xlsx_range",
        "export_xlsx_dataframe",
        "export_xlsx_detected_table_csv",
        "export_xlsx_dataframe_csv",
    }
    assert all(call["middleware"][1]["patch_tool_calls"] is True for call in captured_calls)


def test_office_binary_read_guard_blocks_read_file_for_office_binary() -> None:
    middleware = OfficeBinaryReadGuardMiddleware()
    request = type(
        "Request",
        (),
        {"tool_call": {"name": "read_file", "id": "call_1", "args": {"file_path": "/report.pdf"}}},
    )()

    result = middleware.wrap_tool_call(
        request,
        lambda _request: pytest.fail("read_file handler should not run"),
    )

    assert result.name == "read_file"
    assert result.status == "error"
    assert "read_*_file" in result.content


def test_office_binary_read_guard_allows_text_read_file() -> None:
    middleware = OfficeBinaryReadGuardMiddleware()
    request = type(
        "Request",
        (),
        {"tool_call": {"name": "read_file", "id": "call_1", "args": {"file_path": "/notes.md"}}},
    )()

    result = middleware.wrap_tool_call(
        request,
        lambda _request: "allowed",
    )

    assert result == "allowed"
