from fastapi import APIRouter, Depends, HTTPException, status
from passlib.hash import bcrypt
from sqlmodel import Session, select
from database.connection import get_db
from models.users import User, UserResponse, UserUpdate
from typing import List

admin_router = APIRouter()

# 유저 전체 리스트 호출 /admin/userlist GET
@admin_router.get("/userlist", response_model=List[UserResponse])
def retrieve_all_users(session: Session = Depends(get_db)) -> List[UserResponse]:
    statement = select(User)
    users = session.exec(statement).all()
    session.commit()
    return users  # Pydantic 모델로 자동 변환되어 반환됨


# 특정 유저 정보 호출 /admin/userlist/{user_id} GET
@admin_router.get("/userlist/{user_id}", response_model=UserResponse)
def retrieve_user(user_id: int, session: Session = Depends(get_db)) -> UserResponse:
    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).one_or_none()
    if user:
        return user  # Pydantic 모델로 자동 변환되어 반환됨
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="일치하는 유저가 존재하지 않습니다.",
    )


# 특정 유저 정보 수정 /admin/userlist/{user_id} PUT
@admin_router.put("/userlist/{user_id}")
def update_user(user_id: int, data: UserUpdate, session: Session = Depends(get_db)):
    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).one_or_none()
    if user:
        # 요청 본문으로 전달된 내용 중 값이 있는 항목들만 추출해서 dict 타입으로 변환
        user_data = data.dict(exclude_unset=True)
        # 테이블에서 조회된 결과를 요청을 통해 전달된 값으로 변경
        for key, value in user_data.items():
            setattr(user, key, value)

        session.add(user)
        session.commit()
        session.refresh(user)

        return {"result": "success", "message": "정상적으로 수정"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="일치하는 유저가 존재하지 않습니다.",
    )
