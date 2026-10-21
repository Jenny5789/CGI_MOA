"""명세 2장 계정: 로그인, 회원가입, 내 정보, 로그아웃.

- POST /api/auth/login     : 로그인 (2-1)
- POST /api/auth/register  : 회원가입, 가입 후 바로 로그인 상태 (2-2). 아이디·비밀번호·이메일 필수, 전화번호 선택
- GET  /api/auth/check-username?username= : 아이디 중복확인 (2-6)
- GET  /api/me             : 내 정보 (2-3), 로그인 필요
- POST /api/auth/logout    : 로그아웃, 이 토큰을 더는 받지 않음 (2-4), 로그인 필요
- POST /api/auth/extend    : 로그인 시간 연장 (명세 외 추가 10/15, docs/login_extend.md), 로그인 필요
- 마이페이지 계정 설정 (명세 2-7~2-10, 10/20 추가), 모두 로그인 필요
  - PATCH  /api/me           : 이름·휴대폰 번호·소개 글 수정
  - POST   /api/me/avatar    : 프로필 사진 올리기 (jpg/png, 10MB 이하) / DELETE: 기본 그림으로
  - PATCH  /api/me/email     : 이메일 변경, 지금 비밀번호 확인
  - PATCH  /api/me/password  : 비밀번호 변경, 지금 쓰는 기기만 로그인 유지
- 로그인·회원가입·연장 응답의 expires_at: 이 시각이 지나면 토큰 만료 (한국 시간)
- 회원·토큰은 MySQL(backend/db.py), 시험용 회원 test / test1234
"""
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import (bearer_token, current_user, expires_text, extend_token, find_user, find_user_by_email,
                          hash_password, issue_token, normalize_email, normalize_phone, password_ok, revoke_other_tokens,
                          revoke_token, username_ok, verify_password)
from backend.config import ALLOWED_FORMATS, AVATAR_SIDE, AVATARS_DIR, MAX_UPLOAD_BYTES
from backend.db import User, get_db, utcnow
from backend.errors import ApiError
from backend.file_keys import signed_url

router = APIRouter()
NAME_MAX = 20  # 이름 최대 글자 수 (화면 MyPage 설정과 같게)
BIO_MAX = 60   # 소개 글 최대 글자 수

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
        raise ApiError(400, "INVALID_USERNAME", "아이디는 공백 없이 12자 이하로 입력해 주세요.")
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
        raise ApiError(400, "INVALID_USERNAME", "아이디는 공백 없이 12자 이하로 입력해 주세요.")
    return {"username": username, "available": find_user(db, username) is None}


def _me_response(user: User):
    # avatar_url: 프로필 사진을 올리지 않았으면 null (화면은 기본 그림 사용)
    has_avatar = bool(user.avatar) and (AVATARS_DIR / user.avatar).is_file()
    return {"id": user.id, "username": user.username, "name": user.name, "email": user.email, "phone": user.phone,
            "bio": user.bio or "", "avatar_url": signed_url(user.avatar) if has_avatar else None}


@router.get("/api/me")
def me(user: User = Depends(current_user)):
    return _me_response(user)


class ProfileBody(BaseModel):
    name: Optional[str] = None   # 보낸 항목만 바꾼다
    phone: Optional[str] = None  # 빈 글자면 번호를 지운다
    bio: Optional[str] = None


@router.patch("/api/me")
def update_profile(body: ProfileBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        name = body.name.strip()
        if not name or len(name) > NAME_MAX:
            raise ApiError(400, "INVALID_NAME", f"이름은 1~{NAME_MAX}자로 입력해 주세요.")
        user.name = name
    if body.phone is not None:
        if body.phone.strip():
            phone = normalize_phone(body.phone)
            if phone is None:
                raise ApiError(400, "INVALID_PHONE", "휴대폰 번호를 010-1234-5678 형식으로 입력해 주세요.")
            user.phone = phone
        else:
            user.phone = None
    if body.bio is not None:
        bio = body.bio.strip()
        if len(bio) > BIO_MAX:
            raise ApiError(400, "INVALID_BIO", f"소개 글은 {BIO_MAX}자 이하로 입력해 주세요.")
        user.bio = bio or None
    db.commit()
    return _me_response(user)


@router.post("/api/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    # 사진 올리기(명세 3-1)와 같은 검사: 10MB 이하 jpg/png, 휴대폰 회전 정보 반영. 저장할 때 EXIF는 남기지 않는다
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(400, "IMAGE_TOO_LARGE", "사진은 10MB 이하만 올릴 수 있습니다.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ApiError(400, "INVALID_IMAGE", "이미지를 읽을 수 없습니다.")
    if img.format not in ALLOWED_FORMATS:
        raise ApiError(400, "INVALID_IMAGE", "jpg 또는 png 사진만 올릴 수 있습니다.")
    img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (AVATAR_SIDE, AVATAR_SIDE), Image.Resampling.LANCZOS)
    name = f"avt_{uuid.uuid4().hex[:12]}.jpg"  # 바꿀 때마다 새 이름 → 브라우저에 남은 예전 사진이 보이지 않게
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    img.save(AVATARS_DIR / name, quality=90)
    user.avatar = name  # 예전 사진 파일은 그대로 둔다
    db.commit()
    return _me_response(user)


@router.delete("/api/me/avatar")
def reset_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.avatar = None
    db.commit()
    return _me_response(user)


class EmailBody(BaseModel):
    email: str
    password: str


@router.patch("/api/me/email")
def change_email(body: EmailBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.password, user.password_hash):
        raise ApiError(400, "WRONG_PASSWORD", "비밀번호가 올바르지 않습니다.")
    email = normalize_email(body.email)
    if email is None:
        raise ApiError(400, "INVALID_EMAIL", "올바른 이메일 주소를 입력해 주세요.")
    if email == user.email:
        raise ApiError(400, "SAME_EMAIL", "지금 쓰는 이메일과 같습니다.")
    if find_user_by_email(db, email) is not None:
        raise ApiError(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")
    user.email = email
    db.commit()
    return _me_response(user)


class PasswordBody(BaseModel):
    current_password: str
    new_password: str


@router.patch("/api/me/password")
def change_password(body: PasswordBody, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(400, "WRONG_PASSWORD", "지금 비밀번호가 올바르지 않습니다.")
    if not password_ok(body.new_password):
        raise ApiError(400, "INVALID_PASSWORD", "비밀번호는 8자 이상이고 숫자를 포함해야 합니다.")
    if body.new_password == body.current_password:
        raise ApiError(400, "SAME_PASSWORD", "지금 비밀번호와 다른 비밀번호를 입력해 주세요.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    revoke_other_tokens(db, user, bearer_token(request))  # 다른 기기에서 로그인한 것은 끊는다
    return {}


@router.post("/api/auth/logout")
def logout(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    revoke_token(db, bearer_token(request))
    return {}


@router.post("/api/auth/extend")
def extend(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # 이미 만료된 토큰은 current_user에서 401 → 연장 불가, 다시 로그인
    return {"expires_at": expires_text(extend_token(db, bearer_token(request)))}
