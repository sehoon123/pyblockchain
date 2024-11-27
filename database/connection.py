import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder, create_logger

# 환경 변수 로드
load_dotenv()

# DB 설정
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))  # MySQL 기본 포트
DB_NAME = os.getenv("DB_NAME")
DB_USERNAME = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# 로컬에서 사용할 포트 (원하는 로컬 포트를 설정하세요)

# DATABASE_URL 설정 (로컬 포트를 통해 연결)
DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"
)

# 엔진 생성
try:
    engine = create_engine(DATABASE_URL, echo=True)
except Exception as e:
    raise e


def conn():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        raise e


def get_session():
    with Session(engine) as session:
        yield session
