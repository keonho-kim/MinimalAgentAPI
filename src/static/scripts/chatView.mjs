import { clearEmptyState, elements, renderEmptyState, scrollToBottom } from "./dom.mjs";
import { renderInto } from "./render.mjs";

export function appendMessage(role, text = "") {
  clearEmptyState();

  const message = document.createElement("article");
  message.className = `message ${role}`;

  const roleLabel = document.createElement("span");
  roleLabel.className = "role";
  roleLabel.textContent = role;

  const content = document.createElement("div");
  content.className = role === "assistant" ? "content markdown" : "content";
  if (role === "assistant") {
    renderInto(content, text);
  } else {
    content.textContent = text;
  }

  message.append(roleLabel, content);
  elements.messages.appendChild(message);
  scrollToBottom();
  return content;
}

export function renderStoredMessages(history) {
  elements.messages.replaceChildren();

  for (const message of history) {
    appendMessage(message.role, message.content);
  }

  renderEmptyState();
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

export function appendThinkSegment(turn) {
  const segment = document.createElement("section");
  segment.className = "think-segment";

  const pill = document.createElement("span");
  pill.className = "think-pill";
  pill.textContent = "THINK";

  const content = document.createElement("div");
  content.className = "think-content content markdown";

  segment.append(pill, content);
  turn.body.appendChild(segment);
  scrollToBottom();
  return content;
}
