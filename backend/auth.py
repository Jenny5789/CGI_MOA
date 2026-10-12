# backend/auth.py
# 간단한 로그인 시스템. 세션ID 랜덤생성 방식을 대체해서
# PC(PyQt)와 웹이 "같은 계정"으로 접속하면 작업 기록이 실제로 동기화되도록 한다.

import hashlib
import os
import secrets
from sqlalchemy.orm import Session
from fastapi import Header, HTTPException, Depends

from db import User, AuthToken, get_session

# ── 비밀번호 해싱 (표준 라이브러리 pbkdf2, 추가 패키지 설치 불필요) ────────
def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$")
    except ValueError:
        return False
    return hash_password(password, salt) == stored_hash


# ── 테스트 계정 시드 ────────────────────────────────────────────────────
# 매번 회원가입 API를 직접 호출하거나 SQL을 손으로 짜서 계정을 만들지 않아도,
# 서버가 뜰 때 정해진 아이디/비번의 계정이 이미 있도록 보장한다.
# (계정 자체는 MySQL에 실제로 존재해야 하므로 DB는 떠 있어야 한다 — 다만
#  "로그인하려고 SQL을 직접 작성할 필요는 없다"는 의미에서 SQL 없이 쓸 수 있다.)
TEST_ACCOUNT_USERNAME = "test"
TEST_ACCOUNT_PASSWORD = "test1234"


def ensure_test_account(db: Session):
    existing = db.query(User).filter(User.username == TEST_ACCOUNT_USERNAME).first()
    if existing:
        return
    user = User(username=TEST_ACCOUNT_USERNAME, password_hash=hash_password(TEST_ACCOUNT_PASSWORD))
    db.add(user)
    db.commit()


# ── 회원가입 / 로그인 로직 ───────────────────────────────────────────────
def register_user(db: Session, username: str, password: str) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token_value = secrets.token_hex(32)
    token = AuthToken(token=token_value, user_id=user.id)
    db.add(token)
    db.commit()
    return token_value


# ── 토큰으로 현재 사용자 식별 (PyQt/웹이 매 요청마다 Authorization 헤더로 보냄) ──
def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_session),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="잘못된 인증 헤더 형식입니다.")
    token_value = authorization.removeprefix("Bearer ").strip()

    token = db.query(AuthToken).filter(AuthToken.token == token_value).first()
    if token is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다. 다시 로그인해주세요.")

    user = db.query(User).filter(User.id == token.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user
