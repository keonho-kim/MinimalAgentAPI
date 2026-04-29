export const elements = {
  form: document.querySelector("#chatForm"),
  messageInput: document.querySelector("#messageInput"),
  messages: document.querySelector("#messages"),
  sendButton: document.querySelector("#sendButton"),
  userIdInput: document.querySelector("#userId"),
  sessionUuidInput: document.querySelector("#sessionUuid"),
  newSessionButton: document.querySelector("#newSession"),
  statusDot: document.querySelector("#statusDot"),
  statusText: document.querySelector("#statusText"),
};

export function randomUuid() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return "session-" + Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export function loadSession() {
  const savedUuid = localStorage.getItem("minial-agent-session-uuid");
  elements.sessionUuidInput.value = savedUuid || randomUuid();
  localStorage.setItem(
    "minial-agent-session-uuid",
    elements.sessionUuidInput.value,
  );
}

export function setStatus(kind, text) {
  elements.statusDot.className = `status-dot ${kind}`;
  elements.statusText.textContent = text;
}

export function renderEmptyState() {
  if (elements.messages.children.length > 0) {
    return;
  }

  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = "메시지를 보내면 DeepAgent의 SSE 응답이 이곳에 표시됩니다.";
  elements.messages.appendChild(empty);
}

export function clearEmptyState() {
  const empty = elements.messages.querySelector(".empty-state");
  if (empty) {
    empty.remove();
  }
}

export function appendMessage(role, text = "") {
  clearEmptyState();

  const message = document.createElement("article");
  message.className = `message ${role}`;

  const roleLabel = document.createElement("span");
  roleLabel.className = "role";
  roleLabel.textContent = role;

  const content = document.createElement("div");
  content.className = role === "assistant" ? "content markdown" : "content";
  content.textContent = text;

  message.append(roleLabel, content);
  elements.messages.appendChild(message);
  scrollToBottom();
  return content;
}

export function appendAssistantTurn() {
  clearEmptyState();

  const message = document.createElement("article");
  message.className = "message assistant assistant-turn";

  const roleLabel = document.createElement("span");
  roleLabel.className = "role";
  roleLabel.textContent = "assistant";

  const body = document.createElement("div");
  body.className = "assistant-turn-body";

  message.append(roleLabel, body);
  elements.messages.appendChild(message);
  scrollToBottom();

  return {
    element: message,
    body,
  };
}

export function appendAssistantSegment(turn) {
  const segment = document.createElement("section");
  segment.className = "assistant-segment";

  const content = document.createElement("div");
  content.className = "content markdown";

  segment.appendChild(content);
  turn.body.appendChild(segment);
  scrollToBottom();
  return content;
}

export function upsertActivity(turn, activityCards, activity) {
  let card = activityCards.get(activity.id);

  if (!card) {
    card = createActivityCard();
    activityCards.set(activity.id, card);
    turn.body.appendChild(card.element);
  }

  renderActivityCard(card, activity);
  scrollToBottom();
}

export function scrollToBottom() {
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function createActivityCard() {
  const element = document.createElement("section");
  element.className = "activity-card";

  const header = document.createElement("div");
  header.className = "activity-header";

  const status = document.createElement("span");
  status.className = "activity-status";

  const title = document.createElement("span");
  title.className = "activity-title";

  const path = document.createElement("span");
  path.className = "activity-path";

  const details = document.createElement("details");
  details.className = "activity-details";

  const summary = document.createElement("summary");
  summary.textContent = "Details";

  const body = document.createElement("pre");
  body.className = "activity-payload";

  details.append(summary, body);
  header.append(status, title);
  element.append(header, path, details);

  return {
    element,
    status,
    title,
    path,
    details,
    body,
  };
}

function renderActivityCard(card, activity) {
  card.element.className = `activity-card ${activity.type} ${activity.status}`;
  card.status.textContent = statusText(activity.status);
  card.title.textContent = activityTitle(activity);

  const summary = activity.summary || {};
  const path = summary.path || extractPath(activity);
  card.path.textContent = path ? path : "";
  card.path.hidden = !path;

  const details = formatSummary(summary);
  card.body.textContent = details;
  card.details.hidden = !details;
}

function activityTitle(activity) {
  if (activity.status === "pending") {
    return `Preparing ${activity.label}`;
  }

  return activity.label || activity.name || activity.type;
}

function statusText(status) {
  if (status === "completed") {
    return "done";
  }

  if (status === "error") {
    return "error";
  }

  if (status === "pending") {
    return "queued";
  }

  return "running";
}

function extractPath(activity) {
  const source = activity.input || activity.output || {};

  if (typeof source !== "object" || source === null) {
    return "";
  }

  return source.file_path || source.path || "";
}

function formatSummary(summary) {
  const lines = [];

  for (const [label, value] of [
    ["path", summary.path],
    ["command", summary.command],
    ["query", summary.query],
    ["description", summary.description],
    ["result", summary.result],
  ]) {
    if (value !== undefined && value !== null && value !== "") {
      lines.push(`${label}: ${value}`);
    }
  }

  return lines.join("\n");
}
