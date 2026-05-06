import { beforeEach, expect, test } from "bun:test";

import type { SessionSummary } from "../ui/src/store/session-store";

installLocalStorage();

beforeEach(() => {
  localStorage.clear();
});

test("removes a session from state and localStorage", async () => {
  const { useSessionStore } = await loadStore();
  const userId = "session-delete-user";
  seedSessions(userId, [
    session("one", "One"),
    session("two", "Two"),
  ]);
  useSessionStore.getState().setUserId(userId);

  useSessionStore.getState().removeSession("two");

  expect(useSessionStore.getState().sessions.map((item) => item.uuid)).toEqual([
    "one",
  ]);
  expect(readSessions(userId).map((item) => item.uuid)).toEqual(["one"]);
});

test("switches to the next session when deleting the active session", async () => {
  const { useSessionStore } = await loadStore();
  const userId = "session-active-delete-user";
  seedSessions(userId, [
    session("one", "One"),
    session("two", "Two"),
  ]);
  localStorage.setItem(activeKey(userId), "one");
  useSessionStore.getState().setUserId(userId);

  const nextUuid = useSessionStore.getState().removeSession("one");

  expect(nextUuid).toBe("two");
  expect(useSessionStore.getState().sessionUuid).toBe("two");
  expect(localStorage.getItem(activeKey(userId))).toBe("two");
});

test("creates a replacement session when deleting the last session", async () => {
  const {
    getSessionHistory,
    saveSessionHistory,
    useSessionStore,
  } = await loadStore();
  const userId = "session-last-delete-user";
  seedSessions(userId, [session("only", "Only")]);
  saveSessionHistory(userId, "only", [{ role: "user", content: "hello" }]);
  useSessionStore.getState().setUserId(userId);

  const nextUuid = useSessionStore.getState().removeSession("only");

  expect(nextUuid).not.toBe("only");
  expect(useSessionStore.getState().sessions).toHaveLength(1);
  expect(useSessionStore.getState().sessions[0].title).toBe("New session");
  expect(getSessionHistory(userId, "only")).toEqual([]);
});

test("renames a session in state and localStorage", async () => {
  const { useSessionStore } = await loadStore();
  const userId = "session-rename-user";
  seedSessions(userId, [session("one", "New session")]);
  useSessionStore.getState().setUserId(userId);

  useSessionStore.getState().renameSession("one", "생성된 제목");

  expect(useSessionStore.getState().sessions[0].title).toBe("생성된 제목");
  expect(readSessions(userId)[0].title).toBe("생성된 제목");
});

test("touch keeps generated titles instead of replacing them with message text", async () => {
  const { useSessionStore } = await loadStore();
  const userId = "session-touch-user";
  seedSessions(userId, [session("one", "생성된 제목")]);
  useSessionStore.getState().setUserId(userId);

  useSessionStore.getState().touchSession("one");

  expect(useSessionStore.getState().sessions[0].title).toBe("생성된 제목");
});

test("touch keeps default titles until generated title arrives", async () => {
  const { useSessionStore } = await loadStore();
  const userId = "session-touch-default-user";
  seedSessions(userId, [session("one", "New session")]);
  useSessionStore.getState().setUserId(userId);

  useSessionStore.getState().touchSession("one");

  expect(useSessionStore.getState().sessions[0].title).toBe("New session");
});

async function loadStore() {
  return await import("../ui/src/store/session-store");
}

function session(uuid: string, title: string): SessionSummary {
  return {
    uuid,
    title,
    updatedAt: Date.now(),
  };
}

function seedSessions(userId: string, sessions: SessionSummary[]) {
  localStorage.setItem(`minial:sessions:${userId}`, JSON.stringify(sessions));
}

function readSessions(userId: string): SessionSummary[] {
  const value = localStorage.getItem(`minial:sessions:${userId}`);
  return value ? (JSON.parse(value) as SessionSummary[]) : [];
}

function activeKey(userId: string) {
  return `minial:active-session:${userId}`;
}

function installLocalStorage() {
  const values = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      clear() {
        values.clear();
      },
      getItem(key: string) {
        return values.get(key) ?? null;
      },
      removeItem(key: string) {
        values.delete(key);
      },
      setItem(key: string, value: string) {
        values.set(key, value);
      },
    },
  });
}
