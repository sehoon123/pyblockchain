from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class Follow(SQLModel, table=True):
    __tablename__ = "follow"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    follower_id: int = Field(foreign_key="users.id", nullable=False)
    followed_id: int = Field(foreign_key="users.id", nullable=False)
    created_date: Optional[date] = Field(default=None)
