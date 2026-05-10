import shutil
import subprocess

import pytest
from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.skills import SkillsMiddleware
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from minial_agent.agents.core import agent_builder
from minial_agent.agents.core.agent_builder import AgentBuilder
from minial_agent.agents.core.system_prompt import CORE_AGENT_SYSTEM_PROMPT
from minial_agent.agents.domain.data_expertise import agent as data_agent
from minial_agent.agents.domain.data_expertise.execution_backend import DataExecutionBackend
from minial_agent.agents.domain.data_expertise.system_prompt import (
    DATA_EXPERTISE_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.data_expertise.subagents.business_analyst.system_prompt import (
    BUSINESS_ANALYST_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.data_expertise.subagents.data_analyst.system_prompt import (
    DATA_ANALYST_SYSTEM_PROMPT,
)
from minial_agent.agents.domain.data_expertise.subagents.data_scientist.system_prompt import (
    DATA_SCIENTIST_SYSTEM_PROMPT,
)
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
        "build_data_expertise_subagents",
        lambda **kwargs: [
            {"name": "data_expertise", "runnable": {"data_agent": kwargs}},
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
        "data_expertise",
    ]
    assert all(
        subagent["runnable"][key]["backend"] is files_backend
        for subagent, key in (
            (subagents[0], "edit_agent"),
            (subagents[1], "edit_agent"),
            (subagents[2], "data_agent"),
        )
    )
    assert all(
        subagent["runnable"][key]["checkpointer"] is captured["checkpointer"]
        for subagent, key in (
            (subagents[0], "edit_agent"),
            (subagents[1], "edit_agent"),
            (subagents[2], "data_agent"),
        )
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
    assert "data_expertise" in CORE_AGENT_SYSTEM_PROMPT
    assert "data analyst, business analyst, and data scientist" in CORE_AGENT_SYSTEM_PROMPT
    assert "XLSX/CSV/JSON dataset analysis" in CORE_AGENT_SYSTEM_PROMPT
    assert "not enough evidence for final dataset analysis" in CORE_AGENT_SYSTEM_PROMPT
    assert "Do not read PDF or office binary files directly" in CORE_AGENT_SYSTEM_PROMPT

    worker_prompts = [
        DOCX_AGENT_SYSTEM_PROMPT,
        HWPX_AGENT_SYSTEM_PROMPT,
        PPTX_AGENT_SYSTEM_PROMPT,
        XLSX_AGENT_SYSTEM_PROMPT,
        DATA_EXPERTISE_SYSTEM_PROMPT,
        DATA_ANALYST_SYSTEM_PROMPT,
        BUSINESS_ANALYST_SYSTEM_PROMPT,
        DATA_SCIENTIST_SYSTEM_PROMPT,
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
    assert "workbook edits" in XLSX_AGENT_SYSTEM_PROMPT
    assert "delegate that work to `data_expertise`" in XLSX_AGENT_SYSTEM_PROMPT
    assert "round-table" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "`uv` environment" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "supported stdin heredoc" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "one worker per turn" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "all three explicitly approve" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/data-analyst/" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/business-analyst/" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/data-scientist/" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert ".md" not in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "round_table.md" not in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "consensus.md" not in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "maintain the round-table transcript" not in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "visible transcript" not in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "Do not create a transcript file" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "Do not create a consensus file" in DATA_EXPERTISE_SYSTEM_PROMPT
    assert "execute" in DATA_ANALYST_SYSTEM_PROMPT
    assert "`uv` environment" in DATA_ANALYST_SYSTEM_PROMPT
    assert "supported stdin heredoc" in DATA_ANALYST_SYSTEM_PROMPT
    assert "JavaScript or HTML" in DATA_ANALYST_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/data-analyst/" in DATA_ANALYST_SYSTEM_PROMPT
    assert "<analysis-title>_analysis.py" in DATA_ANALYST_SYSTEM_PROMPT
    assert "<analysis-title>_summary.csv" in DATA_ANALYST_SYSTEM_PROMPT
    assert "<analysis-title>_visualization.html" in DATA_ANALYST_SYSTEM_PROMPT
    assert "execution-cwd relative paths" in DATA_ANALYST_SYSTEM_PROMPT
    assert "do not fabricate an analysis" in DATA_ANALYST_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/business-analyst/" in BUSINESS_ANALYST_SYSTEM_PROMPT
    assert "`uv` environment" in BUSINESS_ANALYST_SYSTEM_PROMPT
    assert "<analysis-title>_business_review.json" in BUSINESS_ANALYST_SYSTEM_PROMPT
    assert ".md" not in BUSINESS_ANALYST_SYSTEM_PROMPT
    assert "/analysis/<analysis-title>/data-scientist/" in DATA_SCIENTIST_SYSTEM_PROMPT
    assert "`uv` environment" in DATA_SCIENTIST_SYSTEM_PROMPT
    assert "supported stdin heredoc" in DATA_SCIENTIST_SYSTEM_PROMPT
    assert "<analysis-title>_validation.json" in DATA_SCIENTIST_SYSTEM_PROMPT
    assert ".md" not in DATA_SCIENTIST_SYSTEM_PROMPT


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


def test_data_expertise_subagents_use_filesystem_execution_middleware(monkeypatch) -> None:
    captured_calls = []

    def fake_create_agent(**kwargs):
        captured_calls.append(kwargs)
        return {"agent": kwargs}

    def fake_filesystem_middleware(**kwargs):
        return {"filesystem": kwargs}

    def fake_patch_tool_calls_middleware():
        return {"patch_tool_calls": True}

    def fake_subagent_middleware(**kwargs):
        return {"subagents": kwargs}

    def fake_hitl_middleware(**kwargs):
        return {"hitl": kwargs}

    monkeypatch.setattr(data_agent, "create_agent", fake_create_agent)
    monkeypatch.setattr(data_agent, "FilesystemMiddleware", fake_filesystem_middleware)
    monkeypatch.setattr(data_agent, "SubAgentMiddleware", fake_subagent_middleware)
    monkeypatch.setattr(data_agent, "HumanInTheLoopMiddleware", fake_hitl_middleware)
    monkeypatch.setattr(
        data_agent,
        "PatchToolCallsMiddleware",
        fake_patch_tool_calls_middleware,
    )

    model = FakeListChatModel(responses=["ok"])
    backend = FilesystemBackend(
        root_dir="/tmp/minial-data-test",
        virtual_mode=True,
        max_file_size_mb=1024,
    )

    subagents = data_agent.build_data_expertise_subagents(
        model=model,
        backend=backend,
        store=None,
        checkpointer="shared-checkpointer",
    )

    assert [subagent["name"] for subagent in subagents] == ["data_expertise"]
    assert [call["name"] for call in captured_calls] == [
        "data_analyst",
        "business_analyst",
        "data_scientist",
        "data_expertise",
    ]
    assert all(call["model"] is model for call in captured_calls)
    assert all(
        call["checkpointer"] == "shared-checkpointer" for call in captured_calls
    )
    assert [tool.name for tool in captured_calls[3]["tools"]] == [
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
    worker_middlewares = [call["middleware"] for call in captured_calls[:3]]
    assert all(
        isinstance(middleware[0]["filesystem"]["backend"], DataExecutionBackend)
        for middleware in worker_middlewares
    )
    assert all(
        middleware[0]["filesystem"]["max_execute_timeout"] == 600
        for middleware in worker_middlewares
    )
    assert all(
        set(middleware[1]["hitl"]["interrupt_on"]) == {
            "write_file",
            "edit_file",
            "execute",
        }
        for middleware in worker_middlewares
    )
    assert all(
        middleware[2]["patch_tool_calls"] is True
        for middleware in worker_middlewares
    )
    team_middleware = captured_calls[3]["middleware"]
    assert isinstance(team_middleware[0]["filesystem"]["backend"], DataExecutionBackend)
    assert team_middleware[0]["filesystem"]["max_execute_timeout"] == 600
    assert [worker["name"] for worker in team_middleware[1]["subagents"]["subagents"]] == [
        "data_analyst",
        "business_analyst",
        "data_scientist",
    ]
    assert "one visible round-table turn" in team_middleware[1]["subagents"]["task_description"]
    assert set(team_middleware[2]["hitl"]["interrupt_on"]) == {
        "write_file",
        "edit_file",
        "execute",
    }
    assert all(
        config["description"].endswith("Approval scope: data_expertise")
        for config in team_middleware[2]["hitl"]["interrupt_on"].values()
    )
    assert team_middleware[3]["patch_tool_calls"] is True


def test_data_execution_backend_allows_python_and_blocks_other_commands(tmp_path) -> None:
    backend = DataExecutionBackend(tmp_path)

    python_result = backend.execute("python -c 'import pandas; print(2 + 3)'")
    blocked_result = backend.execute("curl https://example.com")

    assert python_result.exit_code == 0
    assert "5" in python_result.output
    assert blocked_result.exit_code == 126
    assert "only python/python3 via uv" in blocked_result.output


def test_data_execution_backend_runs_python_through_uv_project(
    tmp_path,
    monkeypatch,
) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append({"args": args[0], **kwargs})
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="ok",
            stderr="",
        )

    backend = DataExecutionBackend(tmp_path)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = backend.execute("python -c 'print(1)'")

    assert result.exit_code == 0
    assert calls[0]["args"][:5] == [
        "uv",
        "run",
        "--project",
        str(backend._project_root),
        "python",
    ]
    assert calls[0]["cwd"] == tmp_path
    assert calls[0]["input"] is None


def test_data_execution_backend_handles_timeout_bytes_output(tmp_path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=kwargs.get("args", "python slow.py"),
            timeout=kwargs.get("timeout", 120),
            output=b"partial stdout",
            stderr=b"partial stderr",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DataExecutionBackend(tmp_path).execute("python slow.py")

    assert result.exit_code == 124
    assert result.truncated is False
    assert "partial stdout" in result.output
    assert "partial stderr" in result.output
    assert "command timed out" in result.output


def test_data_execution_backend_runs_relative_analysis_script(tmp_path) -> None:
    (tmp_path / "sample.csv").write_text(
        "city,score\nSeoul,5\nBusan,3\n",
        encoding="utf-8",
    )
    analysis_dir = tmp_path / "analysis" / "sample"
    analysis_dir.mkdir(parents=True)
    script_path = analysis_dir / "sample_analysis.py"
    script_path.write_text(
        "\n".join(
            [
                "import csv",
                "from pathlib import Path",
                "rows = list(csv.DictReader(Path('sample.csv').open(encoding='utf-8')))",
                "scores = [int(row['score']) for row in rows]",
                "out = Path('analysis/sample')",
                "out.mkdir(parents=True, exist_ok=True)",
                "Path(out / 'sample_summary.csv').write_text(",
                "    'metric,value\\nrow_count,%d\\naverage_score,%.1f\\n' % (len(rows), sum(scores) / len(scores)),",
                "    encoding='utf-8',",
                ")",
                "Path(out / 'sample_visualization.html').write_text(",
                "    '<!doctype html><title>sample</title><p>rows: %d</p>' % len(rows),",
                "    encoding='utf-8',",
                ")",
                "print('done')",
            ]
        ),
        encoding="utf-8",
    )

    result = DataExecutionBackend(tmp_path).execute(
        "python analysis/sample/sample_analysis.py"
    )

    assert result.exit_code == 0
    assert "done" in result.output
    assert (analysis_dir / "sample_summary.csv").read_text(encoding="utf-8") == (
        "metric,value\nrow_count,2\naverage_score,4.0\n"
    )
    assert (analysis_dir / "sample_visualization.html").is_file()


def test_data_execution_backend_runs_python_heredoc_with_relative_paths(
    tmp_path,
) -> None:
    (tmp_path / "sample.csv").write_text("city,score\nSeoul,5\n", encoding="utf-8")

    result = DataExecutionBackend(tmp_path).execute(
        "\n".join(
            [
                "python - <<'PY'",
                "from pathlib import Path",
                "text = Path('sample.csv').read_text(encoding='utf-8')",
                "print(text.splitlines()[1])",
                "PY",
            ]
        )
    )

    assert result.exit_code == 0
    assert "Seoul,5" in result.output


def test_data_execution_backend_runs_explicit_uv_python_heredoc(tmp_path) -> None:
    result = DataExecutionBackend(tmp_path).execute(
        "\n".join(
            [
                "uv run python - <<PY",
                "print('uv heredoc ok')",
                "PY",
            ]
        )
    )

    assert result.exit_code == 0
    assert "uv heredoc ok" in result.output


def test_data_execution_backend_runs_js_heredoc_when_node_is_available(
    tmp_path,
) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")

    result = DataExecutionBackend(tmp_path).execute(
        "\n".join(
            [
                "node - <<'JS'",
                "console.log('node heredoc ok')",
                "JS",
            ]
        )
    )

    assert result.exit_code == 0
    assert "node heredoc ok" in result.output


def test_data_execution_backend_blocks_unsupported_uv_commands(tmp_path) -> None:
    backend = DataExecutionBackend(tmp_path)

    assert backend.execute("uv add pandas").exit_code == 126
    assert backend.execute("uv pip install pandas").exit_code == 126
    assert backend.execute("uv run bash script.sh").exit_code == 126


def test_data_execution_backend_rejects_unclosed_heredoc(tmp_path) -> None:
    result = DataExecutionBackend(tmp_path).execute(
        "\n".join(
            [
                "python - <<'PY'",
                "print('missing delimiter')",
            ]
        )
    )

    assert result.exit_code == 2
    assert "heredoc delimiter 'PY' was not found" in result.output


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
