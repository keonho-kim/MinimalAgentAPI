import { expect, test } from "bun:test";

import { activityDetailLines } from "../ui/src/lib/activity-summary";
import {
  activityGroupKey,
  activityMessageId,
  mergeActivityEvent,
  normalizeGroupedActivity,
  type ActivityEvent,
} from "../ui/src/lib/activity-grouping";

test("renders workspace skill names without internal paths", () => {
  expect(
    activityDetailLines({
      skills: [
        "writing-guide: Use this writing guide for writing requests.",
        "review-guide: Use this review guide for review requests.",
      ],
      description: "writing-guide",
      path: "/.agents/skills/writing-guide/SKILL.md",
    }),
  ).toEqual([
    "writing-guide: Use this writing guide for writing requests.",
    "review-guide: Use this review guide for review requests.",
  ]);
});

test("renders read skill name without internal path", () => {
  expect(
    activityDetailLines({
      skillName: "writing-guide",
      path: "/.agents/skills/writing-guide/SKILL.md",
      description: "사용한 스킬: writing-guide",
    }),
  ).toEqual(["writing-guide"]);
});

test("keeps regular activity details", () => {
  expect(
    activityDetailLines({
      path: "/report.md",
      description: "파일 읽기",
      result: "ok",
    }),
  ).toEqual(["/report.md", "파일 읽기", "ok"]);
});

test("groups workspace skill checks into a single stream card", () => {
  const first = skillCheckEvent("skills-run-1", "running");
  const second = skillCheckEvent("skills-run-2", "completed");
  const id = activityMessageId(first, "fallback", "stream-1");

  expect(id).toBe("activity-group:stream-1:skills-check");
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(id);

  const merged = mergeActivityEvent(normalizeGroupedActivity(first), second);
  expect(merged.label).toBe("스킬 확인");
  expect(merged.status).toBe("running");
  expect(merged.summary).toMatchObject({ groupedCount: 2 });
});

test("keeps skill reads grouped per skill", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "read-run",
    runId: "read-run",
    name: "read_file",
    label: "스킬 읽기",
    status: "running",
    summary: { skillName: "writing-guide" },
  };

  expect(activityGroupKey(event)).toBe("skill-read:writing-guide");
  expect(activityMessageId(event, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:skill-read:writing-guide",
  );
});

test("maps .agents list activity to skill check group", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "ls-run",
    runId: "ls-run",
    name: "ls",
    label: "파일 목록 확인",
    status: "completed",
    summary: {
      path: "/.agents",
      result: '["/.agents/skills/"]',
    },
  };

  const normalized = normalizeGroupedActivity(event);

  expect(activityGroupKey(event)).toBe("skills-check");
  expect(normalized.label).toBe("스킬 확인");
  expect(activityDetailLines(normalized.summary as Record<string, unknown>)).toEqual([]);
});

test("groups regular file list checks by path", () => {
  const first: ActivityEvent = {
    kind: "activity",
    id: "ls-one",
    runId: "ls-one",
    name: "ls",
    status: "running",
    summary: { path: "/reports" },
  };
  const second: ActivityEvent = {
    kind: "activity",
    id: "ls-two",
    runId: "ls-two",
    name: "ls",
    status: "completed",
    summary: { path: "/reports" },
  };

  expect(activityMessageId(first, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:ls:/reports",
  );
  expect(activityMessageId(second, "fallback", "stream-1")).toBe(
    "activity-group:stream-1:ls:/reports",
  );
});

test("does not group approval activities", () => {
  const event: ActivityEvent = {
    kind: "activity",
    id: "write-run",
    runId: "write-run",
    name: "write_file",
    status: "running",
    summary: { path: "/draft.txt", requiresApproval: true },
  };

  expect(activityGroupKey(event)).toBeNull();
  expect(activityMessageId(event, "fallback", "stream-1")).toBe(
    "activity:write-run",
  );
});

function skillCheckEvent(runId: string, status: string): ActivityEvent {
  return {
    kind: "activity",
    id: runId,
    runId,
    name: "SkillsMiddleware.before_agent",
    label: "스킬 확인",
    status,
    summary: {
      skills: ["writing-guide: Use this writing guide for writing requests."],
    },
  };
}
