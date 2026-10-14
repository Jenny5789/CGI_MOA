"""DB (MySQL) 연결과 표.

- 접속 정보: backend/.env 의 DATABASE_URL (각자 컴퓨터의 MySQL, GitHub에 올리지 않음). 만드는 법: docs/database.md
- 서버가 켜질 때 init_db()가 표가 없으면 만들고, 시험용 회원 test / test1234 를 넣는다
- DB에 접속하지 못해도 서버는 켜진다 (추출·합성은 DB를 안 씀). 그때 로그인 관련 주소만 503
"""
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, select
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
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)  # UTC


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
        log.warning("DATABASE_URL이 없습니다 (backend/.env). 로그인 기능 없이 켭니다. 설정: docs/database.md")
        return
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
        Base.metadata.create_all(engine)
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
    except Exception as e:  # 비밀번호가 담긴 접속 주소는 로그에 남기지 않는다
        log.error("DB에 연결하지 못했습니다 (%s). 로그인 기능 없이 켭니다. 확인: docs/database.md 문제 해결", type(e).__name__)


def get_db():
    """주소 함수에서 Depends(get_db)로 받는 DB 세션"""
    if _SessionLocal is None:
        raise ApiError(503, "DB_UNAVAILABLE", "로그인 서버(DB)에 연결되어 있지 않습니다.")
    with _SessionLocal() as s:
        yield s
