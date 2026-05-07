import { describe, expect, test } from "bun:test";

import { appendAgentUiEvent } from "./chat-messages";
import type { UiMessage } from "./chat-messages";
import type { AgentUiEvent } from "./stream";

describe("chat messages", () => {
  test("merges assistant deltas from the same run", () => {
    let messages: UiMessage[] = [];

    messages = appendAgentUiEvent(messages, assistant("run-1", "네, "), "stream-1");
    messages = appendAgentUiEvent(
      messages,
      assistant("run-1", "확인했습니다."),
      "stream-1",
    );

    expect(messages).toHaveLength(1);
    expect(messages[0].kind).toBe("normal");
    expect(messages[0].content).toBe("네, 확인했습니다.");
  });

  test("splits assistant deltas from different runs", () => {
    let messages: UiMessage[] = [];

    messages = appendAgentUiEvent(
      messages,
      assistant("run-1", "네, 확인해서 핵심만 요약해드릴게요."),
      "stream-1",
    );
    messages = appendAgentUiEvent(
      messages,
      assistant("run-2", "\n\n요약\n문서 내용입니다."),
      "stream-1",
    );

    expect(messages).toHaveLength(2);
    expect(messages[0].content).toBe("네, 확인해서 핵심만 요약해드릴게요.");
    expect(messages[1].content).toBe("\n\n요약\n문서 내용입니다.");
  });

  test("keeps assistant, activity, assistant order across runs", () => {
    let messages: UiMessage[] = [];

    messages = appendAgentUiEvent(messages, assistant("run-1", "확인해볼게요."), "stream-1");
    messages = appendAgentUiEvent(messages, activity("tool-1", "running"), "stream-1");
    messages = appendAgentUiEvent(messages, assistant("run-2", "요약입니다."), "stream-1");

    expect(messages).toHaveLength(3);
    expect(messages[0].kind).toBe("normal");
    expect(messages[1].kind).toBe("activity-block");
    expect(messages[2].kind).toBe("normal");
    expect(messages[2].content).toBe("요약입니다.");
  });

  test("updates earlier activity block without merging assistant runs", () => {
    let messages: UiMessage[] = [];

    messages = appendAgentUiEvent(messages, assistant("run-1", "확인해볼게요."), "stream-1");
    messages = appendAgentUiEvent(messages, activity("tool-1", "running"), "stream-1");
    messages = appendAgentUiEvent(messages, assistant("run-2", "요약입니다."), "stream-1");
    messages = appendAgentUiEvent(messages, activity("tool-1", "completed"), "stream-1");

    expect(messages).toHaveLength(3);
    expect(messages[0].content).toBe("확인해볼게요.");
    expect(messages[1].kind).toBe("activity-block");
    if (messages[1].kind !== "activity-block") {
      throw new Error("expected activity block");
    }
    expect(messages[1].entries[0].status).toBe("completed");
    expect(messages[2].content).toBe("요약입니다.");
  });

  test("keeps legacy assistant deltas without run ids merged", () => {
    let messages: UiMessage[] = [];

    messages = appendAgentUiEvent(messages, { kind: "assistant_delta", text: "a" }, "stream-1");
    messages = appendAgentUiEvent(messages, { kind: "assistant_delta", text: "b" }, "stream-1");

    expect(messages).toHaveLength(1);
    expect(messages[0].content).toBe("ab");
  });
});

function assistant(runId: string, text: string): AgentUiEvent {
  return {
    kind: "assistant_delta",
    runId,
    text,
  };
}

function activity(runId: string, status: "running" | "completed"): AgentUiEvent {
  return {
    kind: "activity",
    type: "tool",
    id: runId,
    runId,
    name: "read_pdf_file",
    label: "PDF 읽기",
    message: "AGENT가 PDF 읽기 작업을 시작합니다.",
    status,
    details: { filename: "report.pdf" },
  };
}
