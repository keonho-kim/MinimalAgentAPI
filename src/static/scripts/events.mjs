const streamedModelRuns = new Set();
const REASONING_BLOCK_TYPES = [
  "reasoning",
  "reasoning_content",
  "thinking",
  "thought",
  "reasoning_delta",
  "thinking_delta",
];
const REASONING_FIELDS = [
  "reasoning_content",
  "reasoning",
  "thinking",
  "thought",
  "reasoning_delta",
  "thinking_delta",
];

export function resetEventNormalization() {
  streamedModelRuns.clear();
}

export function normalizeStreamEvent(raw) {
  if (!raw || typeof raw !== "object") {
    return [];
  }

  const eventName = raw.event || raw.name;

  if (eventName === "on_chat_model_stream" || eventName === "on_llm_stream") {
    return normalizeModelStream(raw);
  }

  if (eventName === "on_chat_model_end" || eventName === "on_llm_end") {
    return normalizeModelEnd(raw);
  }

  if (eventName === "on_tool_start") {
    return [createActivity(raw, "tool", "running", raw.data?.input)];
  }

  if (eventName === "on_tool_end") {
    return [createActivity(raw, "tool", "completed", undefined, raw.data?.output)];
  }

  if (eventName === "on_tool_error") {
    return [createActivity(raw, "tool", "error", undefined, raw.data?.error)];
  }

  if (eventName === "on_retriever_start") {
    return [createActivity(raw, "retriever", "running", raw.data?.input)];
  }

  if (eventName === "on_retriever_end") {
    return [
      createActivity(raw, "retriever", "completed", raw.data?.input, raw.data?.output),
    ];
  }

  if (eventName === "custom" || raw.event === "on_custom_event") {
    return [createActivity(raw, "custom", "running", raw.data)];
  }

  if (eventName === "on_chain_start" || eventName === "on_chain_end") {
    const activity = normalizeVisibleChain(raw, eventName);
    return activity ? [activity] : [{ kind: "ignored" }];
  }

  return [{ kind: "ignored" }];
}

export function extractText(value) {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(extractText).join("");
  }

  if (!value || typeof value !== "object") {
    return "";
  }

  if (isReasoningBlock(value)) {
    return "";
  }

  if (value.type === "text" && typeof value.text === "string") {
    return value.text;
  }

  if (typeof value.text === "string") {
    return value.text;
  }

  if (typeof value.content === "string") {
    return value.content;
  }

  if (Array.isArray(value.content)) {
    return value.content.map(extractText).join("");
  }

  if (value.kwargs) {
    return extractText(value.kwargs);
  }

  return "";
}

function normalizeModelStream(raw) {
  const data = raw.data || {};
  const chunk = data.chunk ?? data.output ?? data.message ?? data;
  const toolCalls = extractToolCalls(chunk);
  const reasoning = extractReasoning(chunk);
  const text = extractText(chunk);
  const events = [];

  if (reasoning || text) {
    if (raw.run_id) {
      streamedModelRuns.add(raw.run_id);
    }
  }

  if (reasoning) {
    events.push({
      kind: "think_delta",
      id: raw.run_id,
      parentIds: raw.parent_ids || [],
      text: reasoning,
    });
  }

  if (text) {
    events.push({
      kind: "assistant_delta",
      id: raw.run_id,
      parentIds: raw.parent_ids || [],
      text,
    });
  }

  for (const toolCall of toolCalls) {
    events.push({
      kind: "activity",
      type: "tool",
      id: toolCall.id || `${raw.run_id}:${toolCall.index ?? events.length}`,
      parentIds: raw.parent_ids || [],
      name: toolCall.name || "tool",
      label: toolCall.name || "tool",
      message: activityMessage(toolCall.name || "tool", "pending"),
      status: "pending",
      input: toolCall.args,
      summary: summarizeActivity(toolCall.name || "tool", toolCall.args),
    });
  }

  return events.length > 0 ? events : [{ kind: "ignored" }];
}

function normalizeModelEnd(raw) {
  if (raw.run_id && streamedModelRuns.has(raw.run_id)) {
    return [{ kind: "ignored" }];
  }

  const data = raw.data || {};
  const output = data.output ?? data.chunk ?? data.message;
  const reasoning = extractReasoning(output);
  const text = extractText(output);
  const events = [];

  if (reasoning) {
    events.push({
      kind: "think_delta",
      id: raw.run_id,
      parentIds: raw.parent_ids || [],
      text: reasoning,
    });
  }

  if (text) {
    events.push({
      kind: "assistant_delta",
      id: raw.run_id,
      parentIds: raw.parent_ids || [],
      text,
    });
  }

  return events.length > 0 ? events : [{ kind: "ignored" }];
}

function extractReasoning(value) {
  if (typeof value === "string") {
    return "";
  }

  if (Array.isArray(value)) {
    return value.map(extractReasoning).join("");
  }

  if (!value || typeof value !== "object") {
    return "";
  }

  if (isReasoningBlock(value)) {
    return extractReasoningBlockText(value);
  }

  const parts = [];

  for (const field of REASONING_FIELDS) {
    const extracted = extractReasoningValue(value[field]);
    if (extracted) {
      parts.push(extracted);
    }
  }

  for (const field of ["kwargs", "additional_kwargs", "response_metadata"]) {
    if (value[field] && typeof value[field] === "object") {
      const extracted = extractReasoning(value[field]);
      if (extracted) {
        parts.push(extracted);
      }
    }
  }

  if (Array.isArray(value.content)) {
    const extracted = extractReasoning(value.content);
    if (extracted) {
      parts.push(extracted);
    }
  }

  return parts.join("");
}

function extractReasoningValue(value) {
  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(extractReasoningValue).join("");
  }

  if (value && typeof value === "object") {
    for (const field of ["text", "content", "summary", "reasoning", "thinking"]) {
      const extracted = extractReasoningValue(value[field]);
      if (extracted) {
        return extracted;
      }
    }
  }

  return "";
}

function extractReasoningBlockText(value) {
  for (const field of ["text", "content", "thinking", "reasoning", "summary"]) {
    const extracted = extractReasoningValue(value[field]);
    if (extracted) {
      return extracted;
    }
  }

  return "";
}

function isReasoningBlock(value) {
  return typeof value.type === "string" && REASONING_BLOCK_TYPES.includes(value.type);
}

function extractToolCalls(value) {
  if (!value || typeof value !== "object") {
    return [];
  }

  const calls = [];
  const content = Array.isArray(value.content) ? value.content : [];

  for (const block of content) {
    if (block?.type === "tool_call" || block?.type === "tool_call_chunk") {
      calls.push({
        id: block.id,
        name: block.name,
        args: parseMaybeJson(block.args),
        index: block.index,
      });
    }
  }

  for (const call of value.tool_calls || []) {
    calls.push({
      id: call.id,
      name: call.name,
      args: call.args,
    });
  }

  for (const call of value.tool_call_chunks || []) {
    calls.push({
      id: call.id,
      name: call.name,
      args: parseMaybeJson(call.args),
      index: call.index,
    });
  }

  return calls;
}

function createActivity(raw, type, status, input, output) {
  const name = raw.name || type;

  return {
    kind: "activity",
    type,
    id: raw.run_id || `${type}:${name}`,
    parentIds: raw.parent_ids || [],
    name,
    label: name,
    message: activityMessage(name, status),
    status,
    input,
    output,
    summary: summarizeActivity(name, input, output),
  };
}

function normalizeVisibleChain(raw, eventName) {
  const name = raw.name || "";
  const looksLikeSubagent =
    name === "task" ||
    name.toLowerCase().includes("subagent");

  if (!looksLikeSubagent) {
    return null;
  }

  return createActivity(
    raw,
    "chain",
    eventName.endsWith("_start") ? "running" : "completed",
    raw.data?.input,
    raw.data?.output,
  );
}

function getSourcePath(raw) {
  const path = [];

  if (Array.isArray(raw.ns)) {
    path.push(...raw.ns);
  }

  if (Array.isArray(raw.metadata?.langgraph_path)) {
    path.push(...raw.metadata.langgraph_path);
  }

  if (raw.metadata?.langgraph_node) {
    path.push(raw.metadata.langgraph_node);
  }

  return path.filter(isMeaningfulSourcePart);
}

function activityMessage(name, status) {
  const label = name || "작업";

  if (status === "running") {
    return `AGENT가 ${label} 작업을 시작합니다.`;
  }

  if (status === "completed") {
    return `AGENT가 ${label} 작업을 완료했습니다.`;
  }

  if (status === "error") {
    return `AGENT가 ${label} 작업 중 오류가 발생했습니다.`;
  }

  return `AGENT가 ${label} 작업을 준비합니다.`;
}

function isMeaningfulSourcePart(part) {
  if (typeof part !== "string") {
    return false;
  }

  return (
    !part.startsWith("__pregel_") &&
    part !== "model" &&
    part !== "tools" &&
    part !== "call_model"
  );
}

function summarizeActivity(name, input, output) {
  const source = objectOrEmpty(input);
  const result = objectOrEmpty(output);

  return {
    path: source.file_path || source.path || result.file_path || result.path,
    command: source.command,
    query: source.query || source.pattern,
    description: source.description,
    result: previewValue(output),
  };
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function previewValue(value) {
  if (value === undefined || value === null) {
    return undefined;
  }

  if (typeof value === "string") {
    return truncate(value);
  }

  if (typeof value === "object") {
    const useful =
      value.message ||
      value.error ||
      value.result ||
      value.output ||
      value.content ||
      value.file_path ||
      value.path;
    return useful ? truncate(String(useful)) : truncate(JSON.stringify(value));
  }

  return truncate(String(value));
}

function truncate(value, maxLength = 700) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength)}...`;
}

function parseMaybeJson(value) {
  if (typeof value !== "string") {
    return value;
  }

  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export const __test__ = {
  extractToolCalls,
  getSourcePath,
  normalizeModelStream,
  normalizeModelEnd,
  summarizeActivity,
};
