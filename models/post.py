from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from typing import Optional
from datetime import date

class Post(SQLModel, table=True):
    __tablename__ = 'post'

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    item_name: Optional[str] = Field(default=None, max_length=20)
    expected_price: Optional[float] = Field(default=None)
    created_date: Optional[date] = Field(default=None)
    updated_date: Optional[date] = Field(default=None)
    dna: Optional[str] = Field(default=None, max_length=70)
    img_url: Optional[str] = Field(default=None, max_length=100)
    is_sold: Optional[bool] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=2000)
    sold_price: Optional[float] = Field(default=None)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "item_name": self.item_name,
            "expected_price": self.expected_price,
            "created_date": self.created_date.isoformat()
            if self.created_date
            else None,
            "updated_date": self.updated_date.isoformat()
            if self.updated_date
            else None,
            "dna": self.dna,
            "img_url": self.img_url,
            "sold_price": self.sold_price,
        }


class PostCreate(BaseModel):
    user_id: int
    item_name: str
    expected_price: float
    dna: str
    img_url: str
    description: str

class SoldPriceRequest(BaseModel):
    sold_price: float

# 게시글 수정을 위한 Pydantic 모델
class PostUpdate(BaseModel):
    item_name: str
    expected_price: float
    description: str
    img_url: Optional[str] = None