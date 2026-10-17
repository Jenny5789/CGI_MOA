"""비밀번호 암호화, 로그인 증표(토큰), 로그인 확인.

- 비밀번호: PBKDF2-SHA256 (파이썬 기본 hashlib, 추가 패키지 없음). 저장 형식 "pbkdf2_sha256$반복수$소금$해시"
- 토큰: 무작위 글자. DB에는 토큰의 SHA-256 해시만 저장 (DB가 새어도 토큰으로 로그인 못 하게)
- 토큰 유효 기간: TOKEN_HOURS (3시간, 10/15 결정). 로그인한 시각부터 셈, 쓰는 중에 저절로 늘지 않음
- 연장: 화면이 만료 전에 사용자에게 묻고, 연장하면 POST /api/auth/extend → 그 시각부터 다시 3시간 (docs/login_extend.md)
- 로그인 필요한 주소: 함수 인자에 user: User = Depends(current_user)
"""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta, timezone

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.db import AuthSession, User, get_db, utcnow
from backend.errors import ApiError
from backend.storage import KST

TOKEN_HOURS = 3
USERNAME_MAX = 12  # 아이디 최대 글자 수 (화면 frontend/src/auth/signupRules.js와 같게)
_ITERATIONS = 600_000
_PASSWORD_RULE = re.compile(r"^(?=.*\d).{8,}$")  # 명세 2-2: 8자 이상, 숫자 포함
# 명세 2-2 이메일: 인증 메일은 보내지 않지만, 형식이 맞아야 하고 한 이메일로 한 번만 가입 (무분별한 가입 방지)
_EMAIL_RULE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")
_PHONE_RULE = re.compile(r"^01[016789]\d{7,8}$")  # 휴대폰 번호 (하이픈 빼고 10~11자리)


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


def username_ok(username: str) -> bool:
    """명세 2-2 아이디: 공백 없이 1~12자 (앞뒤 공백은 미리 지운 값, 10/17 50자 → 12자)"""
    return bool(username) and len(username) <= USERNAME_MAX and not any(c.isspace() for c in username)


def normalize_email(email: str | None) -> str | None:
    """소문자로 맞춘 이메일. 형식이 틀리면 None"""
    e = (email or "").strip().lower()
    return e if len(e) <= 255 and _EMAIL_RULE.match(e) else None


def normalize_phone(phone: str | None) -> str | None:
    """"010-1234-5678" 모양으로 맞춘 휴대폰 번호. 형식이 틀리면 None (빈 값 처리는 부르는 쪽에서)"""
    digits = re.sub(r"[\s-]", "", phone or "")
    if not _PHONE_RULE.match(digits):
        return None
    return f"{digits[:3]}-{digits[3:-4]}-{digits[-4:]}"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def expires_text(expires_at) -> str:
    """DB의 UTC 시각 → 응답용 한국 시간 글자 (예: 2026-10-15T18:20:00+09:00)"""
    return expires_at.replace(tzinfo=timezone.utc).astimezone(KST).isoformat(timespec="seconds")


def issue_token(db: Session, user: User):
    """새 토큰을 만들어 DB에 기록하고 (토큰, 만료 시각)을 돌려준다. 그 김에 만료된 토큰은 지운다"""
    now = utcnow()
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
    token = secrets.token_urlsafe(32)
    row = AuthSession(token_hash=_token_hash(token), user_id=user.id, created_at=now, expires_at=now + timedelta(hours=TOKEN_HOURS))
    db.add(row)
    db.commit()
    return token, row.expires_at


def extend_token(db: Session, token: str):
    """이 토큰의 만료를 지금부터 TOKEN_HOURS 뒤로. 새 만료 시각을 돌려준다 (토큰 글자는 그대로)"""
    row = db.get(AuthSession, _token_hash(token))
    row.expires_at = utcnow() + timedelta(hours=TOKEN_HOURS)
    db.commit()
    return row.expires_at


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


# /docs에 Authorize 버튼과 자물쇠 표시를 띄우는 용도. 토큰이 없거나 형식이 틀려도 여기서 막지 않고(auto_error=False) 아래에서 명세 형식 401
_bearer = HTTPBearer(auto_error=False, description="로그인 응답의 token 값 (Bearer는 빼고 입력)")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    """로그인한 회원. 토큰이 없거나 틀리거나 만료되면 401"""
    token = credentials.credentials.strip() if credentials else None
    if token:
        row = db.get(AuthSession, _token_hash(token))
        if row is not None and row.expires_at > utcnow():
            user = db.get(User, row.user_id)
            if user is not None:
                return user
    raise ApiError(401, "UNAUTHORIZED", "로그인이 필요합니다.")


def find_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))
