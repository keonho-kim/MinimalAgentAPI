export const elements = {
  form: document.querySelector("#chatForm"),
  messageInput: document.querySelector("#messageInput"),
  messages: document.querySelector("#messages"),
  sendButton: document.querySelector("#sendButton"),
  userIdInput: document.querySelector("#userId"),
  sessionUuidInput: document.querySelector("#sessionUuid"),
  activeSessionLabel: document.querySelector("#activeSessionLabel"),
  sessionList: document.querySelector("#sessionList"),
  newSessionButton: document.querySelector("#newSession"),
  fileDrawer: document.querySelector("#fileDrawer"),
  fileDrawerToggle: document.querySelector("#fileDrawerToggle"),
  fileDrawerClose: document.querySelector("#fileDrawerClose"),
  fileRefreshButton: document.querySelector("#fileRefresh"),
  fileUploadForm: document.querySelector("#fileUploadForm"),
  fileInput: document.querySelector("#fileInput"),
  fileList: document.querySelector("#fileList"),
  fileDrawerStatus: document.querySelector("#fileDrawerStatus"),
  statusDot: document.querySelector("#statusDot"),
  statusText: document.querySelector("#statusText"),
};

export function randomUuid() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return "session-" + Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export function renderSessionList(sessions, activeUuid) {
  elements.sessionList.replaceChildren();

  for (const session of sessions) {
    const row = document.createElement("div");
    row.className = "session-item";
    row.dataset.uuid = session.uuid;
    row.setAttribute("aria-current", String(session.uuid === activeUuid));

    const button = document.createElement("button");
    button.className = "session-select";
    button.type = "button";
    button.dataset.uuid = session.uuid;
    button.setAttribute("aria-pressed", String(session.uuid === activeUuid));

    const title = document.createElement("span");
    title.className = "session-title";
    title.textContent = session.title || "New session";

    const meta = document.createElement("span");
    meta.className = "session-meta";
    meta.textContent = session.uuid;

    const deleteButton = document.createElement("button");
    deleteButton.className = "session-delete";
    deleteButton.type = "button";
    deleteButton.dataset.uuid = session.uuid;
    deleteButton.title = "Delete conversation";
    deleteButton.setAttribute("aria-label", `Delete ${session.title || session.uuid}`);
    deleteButton.textContent = "×";

    button.append(title, meta);
    row.append(button, deleteButton);
    elements.sessionList.appendChild(row);
  }
}

export function setActiveSessionLabel(uuid) {
  elements.activeSessionLabel.textContent = uuid;
}

export function setStatus(kind, text) {
  elements.statusDot.className = `status-dot ${kind}`;
  elements.statusText.textContent = text;
}

export function clearEmptyState() {
  const empty = elements.messages.querySelector(".empty-state");
  if (empty) {
    empty.remove();
  }
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

export function scrollToBottom() {
  elements.messages.scrollTop = elements.messages.scrollHeight;
}
