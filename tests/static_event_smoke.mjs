import assert from "node:assert/strict";
import {
  normalizeStreamEvent,
  resetEventNormalization,
} from "../src/static/scripts/events.mjs";
import {
  activityRenderKey,
  activityTitleText,
  shouldRenderActivity,
} from "../src/static/scripts/format.mjs";

resetEventNormalization();

const textEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "model-run",
  parent_ids: [],
  data: {
    chunk: {
      content: [{ type: "text", text: "hello" }],
    },
  },
});

assert.equal(textEvents[0].kind, "assistant_delta");
assert.equal(textEvents[0].text, "hello");

const duplicateEndEvents = normalizeStreamEvent({
  event: "on_chat_model_end",
  run_id: "model-run",
  data: {
    output: {
      content: "hello",
    },
  },
});

assert.equal(duplicateEndEvents[0].kind, "ignored");

resetEventNormalization();

const thinkPrefixEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "think-run",
  data: {
    chunk: "I will now formulate the final response",
  },
});
const answerResumeEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "think-run",
  data: {
    chunk: ". 전문 답변입니다.",
  },
});

assert.equal(thinkPrefixEvents[0].kind, "assistant_delta");
assert.equal(thinkPrefixEvents[0].text, "I will now formulate the final response");
assert.equal(answerResumeEvents[0].kind, "assistant_delta");
assert.equal(answerResumeEvents[0].text, ". 전문 답변입니다.");

const structuredReasoningEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "structured-think-run",
  data: {
    chunk: {
      reasoning_content: "I should be concise.",
      content: "간단히 답변하겠습니다.",
    },
  },
});

assert.equal(structuredReasoningEvents[0].kind, "think_delta");
assert.equal(structuredReasoningEvents[0].text, "I should be concise.");
assert.equal(structuredReasoningEvents[1].kind, "assistant_delta");
assert.equal(structuredReasoningEvents[1].text, "간단히 답변하겠습니다.");

const selectorStartEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "selector-run",
  data: {
    chunk: '{"',
  },
});
const selectorEndEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "selector-run",
  data: {
    chunk: 'tools": ["grep"]}',
  },
});
const normalJsonTextEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "json-answer-run",
  data: {
    chunk: '{"result": "ok"}',
  },
});

assert.equal(selectorStartEvents[0].kind, "ignored");
assert.equal(selectorEndEvents[0].kind, "ignored");
assert.equal(normalJsonTextEvents[0].kind, "assistant_delta");
assert.equal(normalJsonTextEvents[0].text, '{"result": "ok"}');

resetEventNormalization();

const nonStreamingEndEvents = normalizeStreamEvent({
  event: "on_chat_model_end",
  run_id: "non-streaming-model-run",
  data: {
    output: {
      content: "final answer",
    },
  },
});

assert.equal(nonStreamingEndEvents[0].kind, "assistant_delta");
assert.equal(nonStreamingEndEvents[0].text, "final answer");

const toolIntentEvents = normalizeStreamEvent({
  event: "on_chat_model_stream",
  run_id: "model-run",
  data: {
    chunk: {
      content: [
        {
          type: "tool_call_chunk",
          id: "tool-call-1",
          name: "write_file",
          args: '{"file_path":"/README.md"}',
          index: 0,
        },
      ],
    },
  },
});

assert.equal(toolIntentEvents[0].kind, "activity");
assert.equal(toolIntentEvents[0].status, "pending");
assert.equal(toolIntentEvents[0].label, "write_file");
assert.deepEqual(toolIntentEvents[0].input, { file_path: "/README.md" });
assert.equal(toolIntentEvents[0].details.path, "/README.md");
assert.equal("raw" in toolIntentEvents[0], false);
assert.equal("sourcePath" in toolIntentEvents[0], false);

const toolStartEvents = normalizeStreamEvent({
  event: "on_tool_start",
  name: "write_file",
  run_id: "tool-run",
  parent_ids: ["model-run"],
  data: {
    input: { file_path: "/README.md", content: "# Test" },
  },
});

assert.equal(toolStartEvents[0].kind, "activity");
assert.equal(toolStartEvents[0].status, "running");
assert.equal(toolStartEvents[0].id, "tool-run");
assert.deepEqual(toolStartEvents[0].parentIds, ["model-run"]);
assert.equal(toolStartEvents[0].message, "AGENT가 write_file 작업을 시작합니다.");
assert.equal(toolStartEvents[0].details.path, "/README.md");

const toolEndEvents = normalizeStreamEvent({
  event: "on_tool_end",
  name: "write_file",
  run_id: "tool-run",
  data: {
    output: { ok: true },
  },
});

assert.equal(toolEndEvents[0].status, "completed");
assert.deepEqual(toolEndEvents[0].output, { ok: true });

const toolErrorEvents = normalizeStreamEvent({
  event: "on_tool_error",
  name: "write_file",
  run_id: "tool-run",
  data: {
    error: "boom",
  },
});

assert.equal(toolErrorEvents[0].status, "error");
assert.equal(toolErrorEvents[0].output, "boom");

const internalChainEvents = normalizeStreamEvent({
  event: "on_chain_end",
  name: "model",
  run_id: "chain-run",
  metadata: {
    langgraph_node: "model",
  },
  data: {
    output: { content: "internal" },
  },
});

assert.equal(internalChainEvents[0].kind, "ignored");

assert.equal(
  shouldRenderActivity({ status: "pending" }),
  false,
);
assert.equal(
  shouldRenderActivity({ status: "running" }),
  true,
);
assert.equal(
  activityTitleText({
    name: "write_file",
    status: "running",
    message: "AGENT가 파일 작성을 시작합니다.",
  }),
  "AGENT가 파일 작성을 시작합니다.",
);
assert.equal(
  activityRenderKey({ id: "tool-run", status: "running" }),
  "tool-run",
);
assert.equal(
  activityRenderKey({ id: "tool-run", status: "completed" }),
  "tool-run",
);
