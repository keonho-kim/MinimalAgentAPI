from pathlib import Path

from minial_agent.api.skills.schema import SkillListItem, SkillSearchResponse
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root


class SkillsService:
    def search_skills(
        self,
        *,
        user_id: str,
        uuid: str,
        query: str,
        limit: int = 10,
    ) -> SkillSearchResponse:
        workspace = ensure_upload_workspace(get_workspace_root(user_id, uuid))
        clean_query = query.strip().lower()
        matches: list[SkillListItem] = []

        for skill_file in sorted(workspace.skills_dir.glob("*/SKILL.md")):
            metadata = _skill_metadata(skill_file)
            name = metadata.get("name") or skill_file.parent.name
            description = metadata.get("description") or ""
            searchable = f"{name}\n{description}".lower()
            if clean_query and clean_query not in searchable:
                continue

            matches.append(
                SkillListItem(
                    name=name,
                    description=description,
                    path=f"/.agents/skills/{skill_file.parent.name}/SKILL.md",
                )
            )
            if len(matches) >= max(1, limit):
                break

        return SkillSearchResponse(matches=matches)


def _skill_metadata(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not text.startswith("---"):
        return {}

    metadata: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if not separator:
            continue
        clean_key = key.strip()
        if clean_key in {"name", "description"}:
            metadata[clean_key] = value.strip().strip("\"'")

    return metadata


skills_service = SkillsService()
