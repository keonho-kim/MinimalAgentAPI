import { describe, expect, test } from "bun:test";

import {
  activityTimelineSummary,
  activityTraceEntry,
  appendActivityEntry,
  completeActivityEntries,
} from "./activity-timeline";
import { displayFileMentionLabel } from "./file-mentions";
import type { AgentUiEvent } from "./stream";

type ActivityEvent = Extract<AgentUiEvent, { kind: "activity" }>;

describe("activity timeline", () => {
  test("merges pending, running, and completed into one entry", () => {
    const pending = trace(
      activity({
        id: "call-1",
        runId: "model-1",
        status: "pending",
      }),
    );
    const running = trace(
      activity({
        id: "tool-1",
        runId: "tool-1",
        status: "running",
      }),
    );
    const completed = trace(
      activity({
        id: "tool-1",
        runId: "tool-1",
        status: "completed",
      }),
    );

    const entries = [pending, running, completed].reduce(
      appendActivityEntry,
      [],
    );

    expect(entries).toHaveLength(1);
    expect(entries[0].status).toBe("completed");
    expect(entries[0].detail).toBe("Read agent.py");
  });

  test("updates an earlier activity block after assistant text arrives", async () => {
    installLocalStorage();
    const { appendAgentUiEvent } = await import("./chat-messages");
    const running = activity({
      id: "tool-1",
      runId: "tool-1",
      status: "running",
    });
    const completed = activity({
      id: "tool-1",
      runId: "tool-1",
      status: "completed",
    });

    let messages: import("./chat-messages").UiMessage[] = [];
    messages = appendAgentUiEvent(messages, running, "stream-1");
    messages = appendAgentUiEvent(
      messages,
      { kind: "assistant_delta", text: "완료했습니다." },
      "stream-1",
    );
    messages = appendAgentUiEvent(messages, completed, "stream-1");

    expect(messages).toHaveLength(2);
    expect(messages[0].kind).toBe("activity-block");
    if (messages[0].kind !== "activity-block") {
      throw new Error("expected activity block");
    }
    expect(messages[0].entries).toHaveLength(1);
    expect(messages[0].entries[0].status).toBe("completed");
    expect(messages[1].content).toBe("완료했습니다.");
  });

  test("summarizes search, list, command, file, and subagent activity", () => {
    const entries = [
      trace(activity({ name: "grep", details: { query: "agent" } })),
      trace(activity({ name: "ls", details: { path: "/office_file_agent" } })),
      trace(activity({ name: "execute", details: { description: "git status --short" } })),
      trace(activity({ name: "write_file", details: { filename: "report.md" } })),
      trace(activity({ name: "edit_file", details: { filename: "agent.py" } })),
      trace(activity({ name: "read_file", details: { filename: "system_prompt.py" } })),
      trace(activity({ name: "task", details: { agentName: "agent_docx" } })),
    ];

    expect(activityTimelineSummary(entries)).toBe(
      "검색 1회, 목록 1개 탐색, 명령어 1개 실행, 파일 1개 생성, 파일 1개 편집, 파일 1개 탐색, 서브에이전트 1개 위임함",
    );
  });

  test("starts a new entry after a completed entry with the same key", () => {
    const first = trace(
      activity({
        id: "tool-1",
        runId: "tool-1",
        status: "completed",
      }),
    );
    const second = trace(
      activity({
        id: "tool-2",
        runId: "tool-2",
        status: "pending",
      }),
    );

    const entries = [first, second].reduce(appendActivityEntry, []);

    expect(entries).toHaveLength(2);
    expect(entries[0].status).toBe("completed");
    expect(entries[1].status).toBe("pending");
  });

  test("marks open entries completed when a stream finishes", () => {
    const entries = completeActivityEntries([
      trace(activity({ status: "running" })),
      trace(activity({ id: "tool-2", runId: "tool-2", status: "pending" })),
      trace(activity({ id: "tool-3", runId: "tool-3", status: "error" })),
    ]);

    expect(entries[0].status).toBe("completed");
    expect(entries[1].status).toBe("completed");
    expect(entries[2].status).toBe("error");
  });

  test("hides a leading slash from file mention labels", () => {
    expect(displayFileMentionLabel("/folder/report.pdf")).toBe("folder/report.pdf");
  });
});

function activity(overrides: Partial<ActivityEvent> = {}): ActivityEvent {
  return {
    kind: "activity",
    type: "tool",
    id: "tool-1",
    runId: "tool-1",
    name: "read_file",
    label: "파일 읽기",
    message: "AGENT가 파일 읽기를 시작합니다.",
    status: "running",
    details: { filename: "agent.py" },
    ...overrides,
  };
}

function trace(event: ActivityEvent) {
  const entry = activityTraceEntry(event);
  if (!entry) {
    throw new Error("expected activity trace entry");
  }
  return entry;
}

function installLocalStorage() {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem(key: string) {
        return store.get(key) ?? null;
      },
      setItem(key: string, value: string) {
        store.set(key, value);
      },
      removeItem(key: string) {
        store.delete(key);
      },
    },
  });
}
