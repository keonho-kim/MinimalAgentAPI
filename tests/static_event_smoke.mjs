import assert from "node:assert/strict";
import {
  normalizeStreamEvent,
  resetEventNormalization,
} from "../src/static/scripts/events.mjs";

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
assert.equal(toolIntentEvents[0].label, "Write file");
assert.deepEqual(toolIntentEvents[0].input, { file_path: "/README.md" });
assert.equal(toolIntentEvents[0].summary.path, "/README.md");
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
assert.equal(toolStartEvents[0].summary.path, "/README.md");

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
