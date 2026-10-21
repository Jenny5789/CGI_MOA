"""DB (MySQL) 연결과 표.

- 접속 정보: backend/.env 의 DATABASE_URL (각자 컴퓨터의 MySQL, GitHub에 올리지 않음). 만드는 법: docs/database.md
- 서버가 켜질 때 init_db()가 표가 없으면 만들고, 시험용 회원 test / test1234 를 넣는다
- 예전에 만든 표에 새 칸이 없으면 추가한다 (_add_missing_columns, 10/17 회원가입 전화번호 phone, 10/20 소개 글 bio·프로필 사진 avatar)
- DB에 접속하지 못해도 서버는 켜진다 (추출·합성은 DB를 안 씀). 그때 로그인 관련 주소만 503
"""
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import ROOT
from backend.errors import ApiError

log = logging.getLogger("uvicorn.error")

load_dotenv(ROOT / "backend" / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

TEST_USER = {"username": "test", "password": "test1234", "name": "MOA User", "email": "moa.user@example.com"}


class Base(DeclarativeBase):
    pass


class User(Base):
    """회원 (명세 2-2, 2-3)"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # 원문은 저장하지 않음 (auth.py)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 회원가입 필수 (10/17), 예전 회원은 비어 있을 수 있음
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 선택, "010-1234-5678" 형식으로 저장
    bio: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 마이페이지 소개 글 (10/20)
    avatar: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 프로필 사진 파일 이름 avt_xxx.jpg (10/20)
    created_at: Mapped[datetime] = mapped_column(DateTime)  # UTC


class UploadedImage(Base):
    """올린 사진 기록 (명세 3-1, 3-2, 10/17). 합성하기 "최근 사용한 사진" 목록용.
    사진 파일은 지금처럼 storage/images에 두고, 여기엔 목록에 필요한 정보만. RECENT_IMAGE_KEEP_HOURS가 지난 기록은
    목록을 볼 때 지운다 (파일은 그대로, 추출·합성·결과에 계속 쓰일 수 있어서)"""
    __tablename__ = "images"

    image_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # garment 상의 사진 / person 인물 사진
    filename: Mapped[str] = mapped_column(String(64))
    thumb: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 작은 사진 파일 이름 (긴 변 240px)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))  # 올린 파일의 SHA-256. 같은 파일은 목록에 한 번만
    from_sample: Mapped[bool] = mapped_column(Boolean, default=False)  # 예시 사진에서 고른 것 (최근 목록에서 뺌)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # UTC


class AuthSession(Base):
    """로그인 증표 (명세 2-1, 2-4). 토큰 원문 대신 해시를 저장한다"""
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # UTC


_SessionLocal = None


def utcnow():
    """DB에는 시간대 없는 UTC로 저장"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_db():
    """표 만들기 + 시험용 회원 넣기. 실패하면 로그만 남기고 넘어간다 (서버는 계속 켜짐)"""
    global _SessionLocal
    if not DATABASE_URL:
        log.warning("DATABASE_URL이 없습니다 (backend/.env). 로그인 기능 없이 켭니다. 설정: docs/database.md 2-3. 접속 설정 파일 생성")
        return
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
        Base.metadata.create_all(engine)
        _add_missing_columns(engine)
        SessionLocal = sessionmaker(engine, expire_on_commit=False)
        with SessionLocal() as s:
            if s.scalar(select(User).where(User.username == TEST_USER["username"])) is None:
                from backend.auth import hash_password
                s.add(User(
                    username=TEST_USER["username"], password_hash=hash_password(TEST_USER["password"]),
                    name=TEST_USER["name"], email=TEST_USER["email"], created_at=utcnow(),
                ))
                s.commit()
        _SessionLocal = SessionLocal
        log.info("DB 연결 완료 (로그인 기능 사용 가능)")
    except Exception as e:
        # MySQL이 돌려준 오류 문장만 남긴다 (비밀번호가 담긴 접속 주소는 남기지 않음)
        reason = getattr(e, "orig", None) or e
        log.error("DB에 연결하지 못했습니다: %s. 로그인 기능 없이 켭니다. 조치: docs/database.md 4. 오류별 조치", reason)


def _add_missing_columns(engine):
    """create_all은 이미 있는 표를 고치지 않으므로, 나중에 생긴 칸은 여기서 추가한다 (데이터는 그대로)"""
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    added = {"phone": "VARCHAR(20)", "bio": "VARCHAR(100)", "avatar": "VARCHAR(64)"}  # 10/17 전화번호, 10/20 소개 글·프로필 사진
    for name, kind in added.items():
        if name not in cols:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {kind} NULL"))
            log.info("users 표에 %s 칸을 추가했습니다", name)


def get_db():
    """주소 함수에서 Depends(get_db)로 받는 DB 세션"""
    if _SessionLocal is None:
        raise ApiError(503, "DB_UNAVAILABLE", "로그인 서버(DB)에 연결되어 있지 않습니다.")
    with _SessionLocal() as s:
        yield s
