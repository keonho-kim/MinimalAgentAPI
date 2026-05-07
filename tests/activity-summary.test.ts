import { expect, test } from "bun:test";

import { activityDetailLines } from "../ui/src/lib/activity-summary";
import {
  activityGroupKey,
  activityMessageId,
  mergeActivityEvent,
  normalizeGroupedActivity,
  type ActivityEvent,
} from "../ui/src/lib/activity-grouping";

test("renders workspace skill names without internal paths", () => {
  expect(
    activityDetailLines({
      skills: [
        "writing-guide: Use this writing guide for writing requests.",
        "review-guide: Use this review guide for review requests.",
      ],
      description: "writing-guide",
      path: "/.agents/skills/writing-guide/SKILL.md",
    }),
  ).toEqual([
    "writing-guide: Use this writing guide for writing requests.",
    "review-guide: Use this review guide for review requests.",
  ]);
});

test("renders read skill name without internal path", () => {
  expect(
    activityDetailLines({
      skillName: "writing-guide",
      path: "/.agents/skills/writing-guide/SKILL.md",
      description: "사용한 스킬: writing-guide",
    }),
  ).toEqual(["writing-guide"]);
});

test("keeps regular activity details", () => {
  expect(
    activityDetailLines({
      path: "/report.md",
      description: "파일 읽기",
      result: "ok",
    }),
  ).toEqual(["/report.md", "파일 읽기", "ok"]);
});

test("drops raw runtime object details", () => {
  expect(
    activityDetailLines({
      result:
        "Command(update={'messages': [AIMessage(content='raw')]}, goto='editor_docx')",
      description: "PDF 분석",
    }),
  ).toEqual(["PDF 분석"]);
});

test("groups workspace skill checks into a single stream card", () => {
  const first = skillCheckEvent("skills-run-1", "running");
  const second = skillCheckEvent("skills-run-2", "completed");
  const id = activityMessageId(first, "fallback", "stream-1");

  expect(id).toBe("activity-group:stream-1:skills-check");
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(id);

  const merged = mergeActivityEvent(normalizeGroupedActivity(first), second);
  expect(merged.label).toBe("스킬 확인");
  expect(merged.status).toBe("running");
  expect(merged.summary).toMatchObject({
    activityLogs: [
      {
        id: "skills-run-2",
        label: "스킬 확인",
        status: "completed",
      },
    ],
  });
});

test("keeps skill reads grouped per skill", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "read-run",
    runId: "read-run",
    name: "read_file",
    label: "스킬 읽기",
    status: "running",
    summary: { skillName: "writing-guide" },
  };

  expect(activityGroupKey(event)).toBe("skill-read:writing-guide");
  expect(activityMessageId(event, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:skill-read:writing-guide",
  );
});

test("maps .agents list activity to skill check group", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "ls-run",
    runId: "ls-run",
    name: "ls",
    label: "파일 목록 확인",
    status: "completed",
    summary: {
      path: "/.agents",
      result: '["/.agents/skills/"]',
    },
  };

  const normalized = normalizeGroupedActivity(event);

  expect(activityGroupKey(event)).toBe("skills-check");
  expect(normalized.label).toBe("스킬 확인");
  expect(activityDetailLines(normalized.summary as Record<string, unknown>)).toEqual([]);
});

test("groups regular file list checks by path", () => {
  const first: ActivityEvent = {
    kind: "activity",
    id: "ls-one",
    runId: "ls-one",
    name: "ls",
    status: "running",
    summary: { path: "/reports" },
  };
  const second: ActivityEvent = {
    kind: "activity",
    id: "ls-two",
    runId: "ls-two",
    name: "ls",
    status: "completed",
    summary: { path: "/reports" },
  };

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:ls:/reports",
  );
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:ls:/reports",
  );
});

test("groups edit agent steps under their subagent delegation summary", () => {
  const delegation: ActivityEvent = {
    kind: "activity",
    type: "subagent",
    id: "task-run",
    runId: "task-run",
    name: "task",
    label: "서브에이전트 위임",
    message: "AGENT가 서브에이전트 위임을 시작합니다.",
    status: "running",
    summary: { delegationRunId: "task-run", description: "DOCX 수정" },
  };
  const step: ActivityEvent = {
    kind: "activity",
    type: "agent_step",
    id: "docx-agent-run",
    runId: "docx-agent-run",
    parentIds: ["graph-run", "task-run"],
    name: "editor_docx",
    label: "DOCX 에이전트",
    message: "AGENT가 DOCX 작업을 시작합니다.",
    status: "running",
    summary: { delegationRunId: "task-run" },
  };

  expect(activityMessageId(delegation, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:subagent:task-run",
  );
  expect(activityMessageId(step, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:subagent:task-run",
  );

  const merged = mergeActivityEvent(delegation, step);

  expect(merged.label).toBe("서브에이전트 위임");
  expect(merged.summary).toMatchObject({
    description: "DOCX 수정",
    activitySteps: [
      {
        id: "docx-agent-run",
        label: "DOCX 에이전트",
        message: "AGENT가 DOCX 작업을 시작합니다.",
        status: "running",
      },
    ],
  });
  expect((merged.summary as Record<string, unknown>).groupedCount).toBeUndefined();
});

test("groups edit agent steps under their subagent delegation", () => {
  const delegation: ActivityEvent = {
    kind: "activity",
    type: "chain",
    id: "task-run",
    runId: "task-run",
    name: "task",
    label: "서브에이전트 위임",
    message: "AGENT가 서브에이전트 위임을 시작합니다.",
    status: "running",
    summary: { description: "DOCX 수정" },
  };
  const docxStep: ActivityEvent = {
    kind: "activity",
    type: "chain",
    id: "docx-run",
    runId: "docx-run",
    parentIds: ["graph-run", "task-run"],
    name: "editor_docx",
    label: "DOCX 에이전트",
    message: "AGENT가 DOCX 작업을 시작합니다.",
    status: "completed",
    summary: {},
  };

  const id = "activity-group:stream-1:subagent:task-run";

  expect(activityMessageId(delegation, "fallback", "stream-1")).toBe(id);
  expect(activityMessageId(docxStep, "fallback", "stream-1")).toBe(id);

  const merged = mergeActivityEvent(delegation, docxStep);

  expect(merged.label).toBe("서브에이전트 위임");
  expect(merged.summary).toMatchObject({
    description: "DOCX 수정",
    activitySteps: [
      {
        id: "docx-run",
        label: "DOCX 에이전트",
        message: "AGENT가 DOCX 작업을 시작합니다.",
        status: "completed",
      },
    ],
  });
  expect((merged.summary as Record<string, unknown>).groupedCount).toBeUndefined();
});

test("groups repeated tool activities by tool and target", () => {
  const first: ActivityEvent = {
    kind: "activity",
    type: "tool",
    id: "tool-one",
    runId: "tool-one",
    name: "read_pdf_file",
    status: "running",
    summary: { fileId: "file_001" },
  };
  const second: ActivityEvent = {
    kind: "activity",
    type: "tool",
    id: "tool-two",
    runId: "tool-two",
    name: "read_pdf_file",
    status: "completed",
    summary: { fileId: "file_001" },
  };

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:file_001",
  );
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:file_001",
  );
});

test("groups intermediate model outputs and keeps their text collapsed", () => {
  const first: ActivityEvent = {
    kind: "activity",
    type: "model_output",
    id: "model-one:intermediate-output",
    runId: "model-one",
    name: "model",
    status: "completed",
    summary: { intermediateText: "첫 번째 중간 응답" },
  };
  const second: ActivityEvent = {
    kind: "activity",
    type: "model_output",
    id: "model-two:intermediate-output",
    runId: "model-two",
    name: "model",
    status: "completed",
    summary: { intermediateText: "두 번째 중간 응답" },
  };

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:intermediate-model-output",
  );
  const merged = mergeActivityEvent(first, second);

  expect(merged.summary).toMatchObject({
    intermediateTexts: ["첫 번째 중간 응답", "두 번째 중간 응답"],
    activityLogs: [
      {
        id: "model-two",
        name: "model",
        status: "completed",
      },
    ],
  });
  expect(activityDetailLines(merged.summary as Record<string, unknown>)).toEqual([]);
});

test("groups read workflow steps by target file", () => {
  const first = readWorkflowEvent({
    name: "pdf_read_resolve",
    status: "running",
    message: "PDF 파일을 확인합니다.",
    parentId: "pdf-workflow-run",
    summary: { path: "report.pdf", fileType: "pdf", operation: "read" },
  });
  const second = readWorkflowEvent({
    name: "pdf_read_answer",
    status: "completed",
    message: "PDF 답변 근거 정리를 완료했습니다.",
    parentId: "pdf-workflow-run",
    summary: {
      path: "report.pdf",
      fileType: "pdf",
      operation: "read",
      result: "11 relevant pages",
    },
  });

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:report.pdf",
  );
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:report.pdf",
  );

  const merged = mergeActivityEvent(first, second);

  expect(merged.message).toBe("PDF 답변 근거 정리를 완료했습니다.");
  expect(merged.status).toBe("completed");
  expect(activityDetailLines(merged.summary as Record<string, unknown>)).toEqual([
    "report.pdf",
    "11 relevant pages",
  ]);
});

test("keeps separate read workflow invocations separate", () => {
  const first = readWorkflowEvent({
    name: "pdf_read_scan",
    status: "running",
    parentId: "first-workflow-run",
    summary: { path: "first.pdf", fileType: "pdf", operation: "read" },
  });
  const second = readWorkflowEvent({
    name: "pdf_read_scan",
    status: "running",
    parentId: "second-workflow-run",
    summary: { path: "second.pdf", fileType: "pdf", operation: "read" },
  });

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:first.pdf",
  );
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:file-read:pdf:second.pdf",
  );
});

test("groups PDF read tool and workflow into one card", () => {
  const tool = {
    kind: "activity",
    type: "tool",
    id: "tool-run",
    runId: "tool-run",
    name: "read_pdf_file",
    status: "running",
    summary: { path: "/report.pdf" },
  } satisfies ActivityEvent;
  const workflow = readWorkflowEvent({
    name: "pdf_read_scan",
    status: "completed",
    parentId: "workflow-run",
    message: "PDF 페이지 스캔을 완료했습니다. 관련 페이지 1개를 찾았습니다.",
    summary: {
      path: "report.pdf",
      fileType: "pdf",
      operation: "read",
      description: "9 pages",
      result: "9 pages scanned",
    },
  });

  const id = activityMessageId(tool, "fallback", "stream-1");

  expect(id).toBe("activity-group:stream-1:file-read:pdf:report.pdf");
  expect(activityMessageId(workflow, "fallback", "stream-1")).toBe(id);

  const merged = mergeActivityEvent(normalizeGroupedActivity(tool), workflow);
  expect(merged.label).toBe("PDF 읽기");
  expect(activityDetailLines(merged.summary as Record<string, unknown>)).toEqual([
    "report.pdf",
    "9 pages",
    "9 pages scanned",
  ]);
});

test("does not group approval activities", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "write-run",
    runId: "write-run",
    name: "write_file",
    status: "running",
    summary: { path: "/draft.txt", requiresApproval: true },
  };

  expect(activityGroupKey(event)).toBeNull();
  expect(activityMessageId(event, "fallback", "stream-1")).toBe(
    "activity:write-run",
  );
});

function skillCheckEvent(runId: string, status: string): ActivityEvent {
  return {
    kind: "activity",
    id: runId,
    runId,
    name: "SkillsMiddleware.before_agent",
    label: "스킬 확인",
    status,
    summary: {
      skills: ["writing-guide: Use this writing guide for writing requests."],
    },
  };
}

function readWorkflowEvent({
  name,
  status,
  parentId,
  message = "PDF 읽기 작업을 진행합니다.",
  summary = {},
}: {
  name: string;
  status: string;
  parentId: string;
  message?: string;
  summary?: Record<string, unknown>;
}): ActivityEvent {
  return {
    kind: "activity",
    type: "workflow",
    id: `${parentId}:${name}:${status}`,
    runId: `${parentId}:${name}:${status}`,
    parentIds: ["root-run", parentId],
    name,
    label: "PDF 읽기",
    message,
    status,
    summary,
  };
}
