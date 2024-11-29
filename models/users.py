# models/users.py
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re


# 비밀번호 유효성 검사 함수
def validate_password(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    if len(value) < 8:
        raise ValueError("비밀번호는 8글자 이상이어야 합니다.")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("영어를 포함 시켜야 합니다.")
    if not re.search(r"\d", value):
        raise ValueError("숫자를 포함 시켜야 합니다.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("특수문자를 포함시켜야 합니다.")
    return value


# User 모델 정의
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(nullable=False, unique=True, index=True, max_length=255)
    password: str = Field(nullable=False, max_length=255)
    nickname: str = Field(nullable=False, unique=True, max_length=50)
    profile_img: Optional[str] = Field(default=None, max_length=512)
    create_date: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    update_date: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})
    role: str = Field(default="user", nullable=False, max_length=50)


# UserCreate 모델 (Pydantic 모델)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    profile_img: Optional[str] = None

    @field_validator("password")
    def validate_password_field(cls, value):
        return validate_password(value)


# UserResponse 모델
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nickname: str
    profile_img: Optional[str]
    role: str
    create_date : Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})

    class Config:
        from_attributes = True


# UserUpdate 모델
class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    profile_img: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


# MyprofileUpdate 모델
class MyprofileUpdate(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None

    @field_validator("password")
    def validate_password_field(cls, value):
        return validate_password(value)

    class Config:
        from_attributes = True


# UserCreateValidator (유효성 검사 모델)
class UserCreateValidator(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    profile_img: Optional[str] = None

    @field_validator("password")
    def validate_password_field(cls, value):
        return validate_password(value)
