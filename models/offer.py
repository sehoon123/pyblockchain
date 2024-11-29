from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from typing import Optional
from datetime import date

class Offer(SQLModel, table=True):
    __tablename__ = 'offer'

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    post_id: int = Field(foreign_key="post.id", nullable=False)
    offer_price: Optional[float] = Field(default=None)
    created_date: Optional[date] = Field(default=None)
    dna: Optional[str] = Field(default=None, max_length=40)
    is_accepted: Optional[bool] = Field(default=None)

class OfferCreate(BaseModel):
    user_email: str
    post_id: int
    offer_price: float

class OfferAcceptRequest(BaseModel):
    offer_id: int