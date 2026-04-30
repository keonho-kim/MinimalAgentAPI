export const state = {
  chatHistory: [],
  currentSource: null,
};

export function resetChatHistory() {
  state.chatHistory = [];
}

export function setCurrentSource(source) {
  state.currentSource = source;
}

export function closeCurrentSource() {
  if (state.currentSource) {
    state.currentSource.close();
    state.currentSource = null;
  }
}

export function loadSessions(userId) {
  return readJson(sessionsKey(userId), []);
}

export function ensureSession(userId, uuid, fallbackTitle = "New session") {
  const sessions = loadSessions(userId);
  const existing = sessions.find((session) => session.uuid === uuid);
  const now = new Date().toISOString();

  if (existing) {
    existing.updatedAt = existing.updatedAt || now;
    saveSessions(userId, sessions);
    return existing;
  }

  const session = {
    uuid,
    title: fallbackTitle,
    createdAt: now,
    updatedAt: now,
  };
  sessions.unshift(session);
  saveSessions(userId, sessions);
  return session;
}

export function createSession(userId, uuid) {
  const session = ensureSession(userId, uuid);
  setActiveSessionUuid(userId, uuid);
  saveSessionHistory(userId, uuid, []);
  return session;
}

export function getActiveSessionUuid(userId) {
  return localStorage.getItem(activeSessionKey(userId));
}

export function setActiveSessionUuid(userId, uuid) {
  localStorage.setItem(activeSessionKey(userId), uuid);
  localStorage.setItem("minial-agent-session-uuid", uuid);
}

export function loadSessionHistory(userId, uuid) {
  return readJson(historyKey(userId, uuid), []);
}

export function saveSessionHistory(userId, uuid, history) {
  localStorage.setItem(historyKey(userId, uuid), JSON.stringify(history));
}

export function touchSession(userId, uuid, title) {
  const sessions = loadSessions(userId);
  const now = new Date().toISOString();
  const existing = sessions.find((session) => session.uuid === uuid);

  if (existing) {
    existing.title = title || existing.title;
    existing.updatedAt = now;
  } else {
    sessions.unshift({
      uuid,
      title: title || "New session",
      createdAt: now,
      updatedAt: now,
    });
  }

  sessions.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  saveSessions(userId, sessions);
}

export function deleteSession(userId, uuid) {
  const sessions = loadSessions(userId).filter((session) => session.uuid !== uuid);
  saveSessions(userId, sessions);
  localStorage.removeItem(historyKey(userId, uuid));

  if (getActiveSessionUuid(userId) === uuid) {
    localStorage.removeItem(activeSessionKey(userId));
    localStorage.removeItem("minial-agent-session-uuid");
  }

  return sessions;
}

export function initializeSessions(userId, uuidFactory) {
  const legacyUuid = localStorage.getItem("minial-agent-session-uuid");
  let sessions = loadSessions(userId);

  if (sessions.length === 0 && legacyUuid) {
    ensureSession(userId, legacyUuid, "Previous session");
    sessions = loadSessions(userId);
  }

  const session = createSession(userId, uuidFactory());
  state.chatHistory = [];
  return session.uuid;
}

function saveSessions(userId, sessions) {
  localStorage.setItem(sessionsKey(userId), JSON.stringify(sessions.slice(0, 50)));
}

function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || "") || fallback;
  } catch {
    return fallback;
  }
}

function sessionsKey(userId) {
  return `minial-agent:sessions:${userId}`;
}

function activeSessionKey(userId) {
  return `minial-agent:active-session:${userId}`;
}

function historyKey(userId, uuid) {
  return `minial-agent:history:${userId}:${uuid}`;
}
