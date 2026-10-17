"""명세 2장 계정: 로그인, 회원가입, 내 정보, 로그아웃.

- POST /api/auth/login     : 로그인 (2-1)
- POST /api/auth/register  : 회원가입, 가입 후 바로 로그인 상태 (2-2). 아이디·비밀번호·이메일 필수, 전화번호 선택
- GET  /api/auth/check-username?username= : 아이디 중복확인 (2-6)
- GET  /api/me             : 내 정보 (2-3), 로그인 필요
- POST /api/auth/logout    : 로그아웃, 이 토큰을 더는 받지 않음 (2-4), 로그인 필요
- POST /api/auth/extend    : 로그인 시간 연장 (명세 외 추가 10/15, docs/login_extend.md), 로그인 필요
- 로그인·회원가입·연장 응답의 expires_at: 이 시각이 지나면 토큰 만료 (한국 시간)
- 회원·토큰은 MySQL(backend/db.py), 시험용 회원 test / test1234
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import (bearer_token, current_user, expires_text, extend_token, find_user, find_user_by_email,
                          hash_password, issue_token, normalize_email, normalize_phone, password_ok, revoke_token,
                          username_ok, verify_password)
from backend.db import User, get_db, utcnow
from backend.errors import ApiError

router = APIRouter()

# 없는 아이디로 로그인할 때도 비밀번호 확인 시간을 같게 해서, 응답 시간으로 아이디 유무를 알 수 없게
_DUMMY_HASH = hash_password("dummy-password-0")


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    email: Optional[str] = None  # 필수. 비어 있으면 422 대신 우리 오류(INVALID_EMAIL)로 알려 주려고 Optional
    phone: Optional[str] = None  # 선택
    name: Optional[str] = None


def _login_response(db: Session, user: User):
    token, expires_at = issue_token(db, user)
    return {"token": token, "expires_at": expires_text(expires_at), "user": {"id": user.id, "username": user.username, "name": user.name}}


@router.post("/api/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = find_user(db, body.username.strip())
    if not verify_password(body.password, user.password_hash if user else _DUMMY_HASH) or user is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 올바르지 않습니다.")
    return _login_response(db, user)


@router.post("/api/auth/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    username = body.username.strip()
    if not username_ok(username):
        raise ApiError(400, "INVALID_USERNAME", "아이디는 공백 없이 50자 이하로 입력해 주세요.")
    if not password_ok(body.password):
        raise ApiError(400, "INVALID_PASSWORD", "비밀번호는 8자 이상이고 숫자를 포함해야 합니다.")
    email = normalize_email(body.email)
    if email is None:
        raise ApiError(400, "INVALID_EMAIL", "올바른 이메일 주소를 입력해 주세요.")
    phone = None
    if (body.phone or "").strip():
        phone = normalize_phone(body.phone)
        if phone is None:
            raise ApiError(400, "INVALID_PHONE", "휴대폰 번호를 010-1234-5678 형식으로 입력해 주세요.")
    if find_user(db, username) is not None:
        raise ApiError(409, "DUPLICATE_USERNAME", "이미 사용 중인 아이디입니다.")
    if find_user_by_email(db, email) is not None:
        raise ApiError(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")
    name = (body.name or "").strip()[:100] or username
    user = User(username=username, password_hash=hash_password(body.password), name=name, email=email, phone=phone,
                created_at=utcnow())
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 같은 아이디가 동시에 가입된 경우
        db.rollback()
        raise ApiError(409, "DUPLICATE_USERNAME", "이미 사용 중인 아이디입니다.")
    return _login_response(db, user)


@router.get("/api/auth/check-username")
def check_username(username: str = "", db: Session = Depends(get_db)):
    # 회원가입 창의 "중복확인" 버튼. 가입할 때도 다시 확인하므로 여기 결과는 안내용
    username = username.strip()
    if not username_ok(username):
        raise ApiError(400, "INVALID_USERNAME", "아이디는 공백 없이 50자 이하로 입력해 주세요.")
    return {"username": username, "available": find_user(db, username) is None}


@router.get("/api/me")
def me(user: User = Depends(current_user)):
    # avatar_url: 프로필 사진 기능이 아직 없어 null (화면은 기본 그림 사용)
    return {"id": user.id, "username": user.username, "name": user.name, "email": user.email, "phone": user.phone,
            "avatar_url": None}


@router.post("/api/auth/logout")
def logout(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    revoke_token(db, bearer_token(request))
    return {}


@router.post("/api/auth/extend")
def extend(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # 이미 만료된 토큰은 current_user에서 401 → 연장 불가, 다시 로그인
    return {"expires_at": expires_text(extend_token(db, bearer_token(request)))}
