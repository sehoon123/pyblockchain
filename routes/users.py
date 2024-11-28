# routes/users.py
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import  Session, select
from passlib.hash import bcrypt
from jose import JWTError, jwt
import os
from datetime import datetime, timedelta, timezone
from database.connection import  get_db
from models.users import User, UserResponse, UserCreateValidator


user_router = APIRouter()

# JWT 환경 변수 설정
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 환경 변수가 설정되지 않았습니다.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2PasswordBearer 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise HTTPException(status_code=401, detail="JWT Error")

    statement = select(User).where(User.email == email)
    user = db.exec(statement).one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@user_router.post("/signup", response_model=UserResponse)
def signup(user: UserCreateValidator, db: Session = Depends(get_db)):
    try:
        # 이메일 중복 확인
        statement = select(User).where(User.email == user.email)
        db_user = db.exec(statement).one_or_none()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # 닉네임 중복 확인
        statement = select(User).where(User.nickname == user.nickname)
        db_nickname = db.exec(statement).one_or_none()
        if db_nickname:
            raise HTTPException(status_code=400, detail="Nickname already taken")

        # 비밀번호 해싱
        hashed_password = bcrypt.hash(user.password)

        new_user = User(
            email=user.email,
            password=hashed_password,
            nickname=user.nickname,
            profile_img=user.profile_img,
        )
        db.add(new_user)

        db.commit()
        db.refresh(new_user)
        return new_user

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@user_router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    statement = select(User).where(User.email == form_data.username)
    db_user = db.exec(statement).one_or_none()
    if not db_user or not bcrypt.verify(form_data.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.email}, expires_delta=access_token_expires)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "nickname": db_user.nickname,
        "user_email": db_user.email,
        "profile_img": db_user.profile_img,
        "role": db_user.role
    }


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@user_router.get("/validate", response_model=UserResponse)
def validate_token(current_user: UserResponse = Depends(get_current_user)):
    return current_user
