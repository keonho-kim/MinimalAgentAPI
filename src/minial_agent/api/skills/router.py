from fastapi import APIRouter

from minial_agent.api.skills.schema import SkillSearchResponse
from minial_agent.api.skills.service import skills_service


router = APIRouter(prefix="/api/skills")


@router.get("/search", response_model=SkillSearchResponse)
async def search_skills(
    user_id: str,
    uuid: str,
    q: str = "",
    limit: int = 10,
) -> SkillSearchResponse:
    return skills_service.search_skills(
        user_id=user_id,
        uuid=uuid,
        query=q,
        limit=limit,
    )
