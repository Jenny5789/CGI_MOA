# backend/db.py
# MySQL 연결 + 테이블 정의 (SQLAlchemy ORM)
# 접속 정보는 .env 파일에서 읽어온다 (팀원마다 값이 다를 수 있음)

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

load_dotenv()  # backend/.env 파일 읽기

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL이 없습니다. backend/.env.example을 복사해 .env를 만들고 자기 MySQL 접속 정보를 적으세요.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    """로그인 계정. PC(PyQt)와 웹이 같은 계정으로 접속해야 작업 기록이 동기화된다."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthToken(Base):
    """로그인 성공 시 발급하는 토큰. PyQt/웹 클라이언트가 로컬에 저장해두고 재사용한다."""
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, index=True)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Extraction(Base):
    """
    1단계(객체 추출) 결과.
    사용자가 원본 사진에서 객체를 클릭하면 SAM을 '한 번만' 돌려서
    원본 이미지 + 후보 마스크 3개 + 후보별 잘라낸 미리보기(PNG)를 저장해둔다.
    이후 합성 요청은 이 id(+선택된 후보)만 넘기므로 SAM을 다시 돌리지 않는다.

    SAM은 클릭 한 번에 후보 마스크를 3개(작은 부분/중간/전체) 내놓는데,
    애매한 지점을 클릭하면 원하는 것과 다른 후보가 기본으로 뽑힐 수 있어서
    3개를 다 저장해두고 사용자가 마음에 안 들면 다른 후보로 바꿀 수 있게 한다.
    candidate_masks/candidate_cutouts 는 면적이 큰 순서로 정렬된 경로 리스트(JSON),
    active_candidate 는 그중 현재 채택된 인덱스(기본 0 = 가장 큰 후보).
    """
    __tablename__ = "extractions"

    id = Column(String(36), primary_key=True)   # uuid
    user_id = Column(Integer, index=True)

    src_image_path = Column(String(255))         # 사용자가 올린 원본 사진(RGB)

    candidate_masks = Column(Text)                # JSON: 후보 마스크 경로 리스트
    candidate_cutouts = Column(Text)               # JSON: 후보 컷아웃 PNG 경로 리스트
    active_candidate = Column(Integer, default=0)  # 현재 채택된 후보 인덱스

    # 이 마스크를 만들어낸 클릭 점들. JSON: [[x, y, label], ...] (label 1=더하기, 0=빼기)
    # 저장해두는 이유: 같은 결과를 다시 만들려면 어떤 점을 찍었는지가 입력의 일부다.
    points = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def mask_path(self) -> str:
        """현재 채택된 후보의 마스크 경로 (합성 시 이걸 쓴다)."""
        import json
        return json.loads(self.candidate_masks)[self.active_candidate]

    @property
    def cutout_path(self) -> str:
        """현재 채택된 후보의 컷아웃 PNG 경로."""
        import json
        return json.loads(self.candidate_cutouts)[self.active_candidate]


class CompositeJob(Base):
    """합성 작업 1건. 이미지 자체는 DB에 안 넣고 파일 경로만 저장."""
    __tablename__ = "composite_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    client_type = Column(String(16))                   # "pyqt" 또는 "web"

    extraction_id = Column(String(36), index=True)     # 어떤 추출 결과를 썼는지
    ref_image_path = Column(String(255))               # 추출 당시 원본 사진
    ref_mask_path = Column(String(255))                # 추출 당시 SAM 마스크
    bg_image_path = Column(String(255))                # 사용자가 고른 배경
    placement_mask_path = Column(String(255))          # 드래그/리사이즈로 확정한 배치 영역
    result_image_path = Column(String(255), nullable=True)

    status = Column(String(16), default="queued")      # queued / processing / done / failed
    error_message = Column(Text, nullable=True)

    guidance_scale = Column(Integer, default=5)
    # 결과 재현용 시드. 같은 추출물 + 같은 배치 + 같은 시드 = 항상 같은 결과가 나온다.
    # 기록해두면 나중에 "그때 그 이미지"를 그대로 다시 만들 수 있다.
    seed = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """테이블이 없으면 생성. 서버 시작 시 한 번 호출."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """FastAPI 의존성 주입용 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
