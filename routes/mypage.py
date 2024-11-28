from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, UploadFile, File, Form
from sqlmodel import SQLModel, Session, select
from passlib.hash import bcrypt
from pydantic import EmailStr, BaseModel, field_validator
from database.connection import engine, get_db
from models.users import User, UserResponse, MyprofileUpdate
from routes.users import get_current_user
import logging
import os
import boto3
from io import BytesIO

# 환경 변수 및 로깅 설정
SECRET_KEY = os.getenv("SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
)

mypage_router = APIRouter()

# 내 정보 호출 /mypage GET
@mypage_router.get("/", response_model=UserResponse)
def get_mypage(current_user: User = Depends(get_current_user)):
    logging.debug(f"Current user: {current_user}")
    if current_user:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "profile_img": current_user.profile_img,
            "role": current_user.role,
        }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다.")

# 마이페이지 정보 업데이트 /mypage PUT
@mypage_router.put("/")
def update_mypage(
    nickname: str = Form(None),
    password: str = Form(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    profile_img: UploadFile = File(None),  # 이미지 업로드
):
    try:
        # 유저 정보 조회
        statement = select(User).where(User.id == current_user.id)
        result = session.exec(statement)
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다.")

        # 닉네임, 비밀번호 업데이트
        if nickname:
            user.nickname = nickname
        if password:
            user.password = bcrypt.hash(password)

        # 프로필 이미지 업로드
        if profile_img:
            if not profile_img.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="파일 이름이 없습니다.",
                )
            file_extension = os.path.splitext(profile_img.filename)[1]
            file_name = f"profile_images/{current_user.id}/{profile_img.filename}"
            logging.debug(f"Uploading file to S3 with file name: {file_name}")

            try:
                file_content = profile_img.file.read()
                s3_client.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=file_name,
                    Body=BytesIO(file_content),
                    ContentType=profile_img.content_type,
                    ACL="public-read",
                )
                user.profile_img = f"{S3_BASE_URL}/{file_name}"
                logging.debug(f"Updated user profile_img in DB: {user.profile_img}")
            except Exception as e:
                logging.error(f"S3 업로드 실패: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"S3 업로드 실패: {str(e)}",
                )

        # DB 업데이트
        try:
            session.add(user)
            session.commit()
            session.refresh(user)
            logging.debug(f"Final Updated user profile_img in DB: {user.profile_img}")
        except Exception as e:
            session.rollback()
            logging.error(f"Database update failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile.",
            )

        # 응답 반환
        return {
            "result": "success",
            "message": "정상적으로 수정되었습니다.",
            "updated_user": {
                "nickname": user.nickname,
                "profile_img": user.profile_img,
            },
        }

    except Exception as general_e:
        logging.error(f"An unexpected error occurred: {str(general_e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
