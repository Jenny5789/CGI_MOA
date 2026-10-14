"""비밀번호 암호화, 로그인 증표(토큰), 로그인 확인.

- 비밀번호: PBKDF2-SHA256 (파이썬 기본 hashlib, 추가 패키지 없음). 저장 형식 "pbkdf2_sha256$반복수$소금$해시"
- 토큰: 무작위 글자. DB에는 토큰의 SHA-256 해시만 저장 (DB가 새어도 토큰으로 로그인 못 하게)
- 토큰 유효 기간: TOKEN_DAYS (1일, 10/15 결정). 로그인한 때부터 셈, 쓰는 중에도 연장 안 됨
- 로그인 필요한 주소: 함수 인자에 user: User = Depends(current_user)
"""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.db import AuthSession, User, get_db, utcnow
from backend.errors import ApiError

TOKEN_DAYS = 1
_ITERATIONS = 600_000
_PASSWORD_RULE = re.compile(r"^(?=.*\d).{8,}$")  # 명세 2-2: 8자 이상, 숫자 포함


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), _ITERATIONS).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), int(iterations)).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(check, digest)


def password_ok(password: str) -> bool:
    return bool(_PASSWORD_RULE.match(password or ""))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user: User) -> str:
    """새 토큰을 만들어 DB에 기록. 그 김에 만료된 토큰은 지운다"""
    now = utcnow()
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, created_at=now, expires_at=now + timedelta(days=TOKEN_DAYS)))
    db.commit()
    return token


def revoke_token(db: Session, token: str):
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    db.commit()


def bearer_token(request: Request) -> str | None:
    """요청 머리 Authorization: Bearer <토큰> 에서 토큰만 꺼낸다"""
    value = request.headers.get("Authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """로그인한 회원. 토큰이 없거나 틀리거나 만료되면 401"""
    token = bearer_token(request)
    if token:
        row = db.get(AuthSession, _token_hash(token))
        if row is not None and row.expires_at > utcnow():
            user = db.get(User, row.user_id)
            if user is not None:
                return user
    raise ApiError(401, "UNAUTHORIZED", "로그인이 필요합니다.")


def find_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))
