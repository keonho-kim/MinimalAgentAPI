from pydantic import BaseModel


class SkillListItem(BaseModel):
    name: str
    description: str
    path: str


class SkillSearchResponse(BaseModel):
    matches: list[SkillListItem]
