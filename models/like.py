from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from typing import Optional

class Like(SQLModel, table=True):
    __tablename__ = 'like'

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    post_id: int = Field(foreign_key="post.id", nullable=False)


class LikeCreate(BaseModel):
    user_email: str
    post_id: int