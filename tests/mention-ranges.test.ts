import { expect, test } from "bun:test";

import {
  serializeFileMentions,
  syncFileMentionRanges,
  validFileMentionRanges,
} from "../ui/src/lib/file-mentions";

test("serializes mixed file and skill mentions by range order", () => {
  const value = "Use writing-guide with README.md";

  expect(
    serializeFileMentions(value, [
      {
        id: "file-1",
        kind: "file",
        start: 23,
        end: 32,
        label: "README.md",
        href: "/README.md",
      },
      {
        id: "skill-1",
        kind: "skill",
        start: 4,
        end: 17,
        label: "writing-guide",
        href: "/.agents/skills/writing-guide/SKILL.md",
      },
    ]),
  ).toBe(
    "Use [writing-guide](/.agents/skills/writing-guide/SKILL.md) with [README.md](/README.md)",
  );
});

test("drops a mention token when its label is edited", () => {
  const previousValue = "Use writing-guide";
  const nextValue = "Use writing";
  const ranges = validFileMentionRanges(previousValue, [
    {
      id: "skill-1",
      kind: "skill",
      start: 4,
      end: 17,
      label: "writing-guide",
      href: "/.agents/skills/writing-guide/SKILL.md",
    },
  ]);

  expect(
    syncFileMentionRanges({
      previousValue,
      nextValue,
      ranges,
    }),
  ).toEqual([]);
});
