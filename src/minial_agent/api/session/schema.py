from pydantic import BaseModel, Field


class SessionTitleRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    message: str = Field(min_length=1)


class SessionTitleResponse(BaseModel):
    title: str
