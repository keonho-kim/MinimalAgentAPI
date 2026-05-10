import type { ActivityTraceEntry } from "./activity-timeline-types";

export function activityTimelineSummary(entries: ActivityTraceEntry[]) {
  const counts = activityCounts(entries);
  const parts = [
    counts.search ? `검색 ${counts.search}회` : null,
    counts.list ? `목록 ${counts.list}개 탐색` : null,
    counts.command ? `명령어 ${counts.command}개 실행` : null,
    counts.fileCreate ? `파일 ${counts.fileCreate}개 생성` : null,
    counts.fileEdit ? `파일 ${counts.fileEdit}개 편집` : null,
    counts.fileRead ? `파일 ${counts.fileRead}개 탐색` : null,
    counts.subagent ? `서브에이전트 ${counts.subagent}개 위임` : null,
    counts.skills ? `스킬 ${counts.skills}개 확인` : null,
    counts.other ? `작업 ${counts.other}개 진행` : null,
  ].filter((part): part is string => Boolean(part));

  if (!parts.length) {
    return "작업 진행함";
  }

  return `${parts.join(", ")}함`;
}

export function hasRunningActivity(entries: ActivityTraceEntry[]) {
  return entries.some(
    (entry) => entry.status === "pending" || entry.status === "running",
  );
}

export function completeActivityEntries(entries: ActivityTraceEntry[]) {
  return entries.map((entry) =>
    entry.status === "pending" || entry.status === "running"
      ? { ...entry, status: "completed" }
      : entry,
  );
}

function activityCounts(entries: ActivityTraceEntry[]) {
  return entries.reduce(
    (counts, item) => {
      if (item.category === "intermediate") {
        return counts;
      }
      if (item.category === "file-create") {
        counts.fileCreate += 1;
      } else if (item.category === "file-edit") {
        counts.fileEdit += 1;
      } else if (item.category === "file-read") {
        counts.fileRead += 1;
      } else if (item.category === "search") {
        counts.search += 1;
      } else if (item.category === "list") {
        counts.list += 1;
      } else if (item.category === "command") {
        counts.command += 1;
      } else if (item.category === "subagent") {
        counts.subagent += 1;
      } else if (item.category === "skills") {
        counts.skills += 1;
      } else {
        counts.other += 1;
      }
      return counts;
    },
    {
      command: 0,
      fileCreate: 0,
      fileEdit: 0,
      fileRead: 0,
      list: 0,
      other: 0,
      search: 0,
      skills: 0,
      subagent: 0,
    },
  );
}
