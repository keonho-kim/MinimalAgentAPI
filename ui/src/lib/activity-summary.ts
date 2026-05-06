export function activityDetailLines(summary: Record<string, unknown>) {
  const skillName = stringValue(summary.skillName);
  if (skillName) {
    return [skillName];
  }

  const skills = summary.skills;
  if (Array.isArray(skills)) {
    const names = skills.filter(
      (skill): skill is string =>
        typeof skill === "string" && skill.trim().length > 0,
    );
    return names;
  }

  return [
    stringValue(summary.path),
    stringValue(summary.description),
    stringValue(summary.result),
  ].filter((line): line is string => Boolean(line));
}

function stringValue(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return null;
}
