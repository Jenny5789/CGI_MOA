"""계정: 로그인, 회원가입, 내 정보, 로그아웃.

- POST /api/auth/login     : 로그인
- POST /api/auth/register  : 회원가입, 가입 후 바로 로그인 상태. 아이디·비밀번호·이메일 필수, 전화번호 선택
- GET  /api/auth/check-username?username= : 아이디 중복확인
- GET  /api/me             : 내 정보, 로그인 필요
- POST /api/auth/logout    : 로그아웃, 이 토큰을 더는 받지 않음, 로그인 필요
- POST /api/auth/extend    : 로그인 시간 연장 (docs/login_extend.md), 로그인 필요
- 마이페이지 계정 설정, 모두 로그인 필요
  - PATCH  /api/me           : 이름·휴대폰 번호·소개 글 수정
  - POST   /api/me/avatar    : 프로필 사진 올리기 (jpg/png, 10MB 이하) / DELETE: 기본 그림으로
  - PATCH  /api/me/email     : 이메일 변경, 지금 비밀번호 확인
  - PATCH  /api/me/password  : 비밀번호 변경, 지금 쓰는 기기만 로그인 유지
  - DELETE /api/me           : 회원 탈퇴, 지금 비밀번호 확인 뒤 이 회원의 DB 기록과 storage 파일 삭제
- 로그인·회원가입·연장 응답의 expires_at: 이 시각이 지나면 토큰 만료 (한국 시간)
- 회원·토큰은 MySQL(backend/db.py), 시험용 회원 test / test1234
"""
import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import (current_session, current_user, extend_token, find_user, find_user_by_email, hash_password,
                          issue_token, normalize_email, normalize_phone, password_ok, revoke_other_tokens, revoke_token,
                          username_ok, verify_password)
from backend.config import (ALLOWED_FORMATS, AVATAR_SIDE, AVATARS_DIR, EXTRACTIONS_DIR, IMAGES_DIR, JOBS_DIR,
                            MAX_UPLOAD_BYTES, RESULTS_DIR)
from backend.db import AuthSession, Extraction, Job, Result, UploadedImage, User, get_db, kst_text, utcnow
from backend.errors import ApiError
from backend.file_keys import signed_url
from backend.routers import compose
from backend.routers.files import SAFE_NAME

router = APIRouter()
log = logging.getLogger("moa.auth")
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
    email: Optional[str] = None  # 필수. 빠졌을 때 INVALID_REQUEST 대신 INVALID_EMAIL로 알려 주려고 Optional
    phone: Optional[str] = None  # 선택
    name: Optional[str] = None


def _login_response(db: Session, user: User):
    token, expires_at = issue_token(db, user)
    return {"token": token, "expires_at": kst_text(expires_at), "user": {"id": user.id, "username": user.username, "name": user.name}}


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
    # 사진 올리기와 같은 검사: 10MB 이하 jpg/png, 휴대폰 회전 정보 반영. 저장할 때 EXIF는 남기지 않는다
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
    old = user.avatar
    user.avatar = name
    db.commit()
    _remove_files([AVATARS_DIR / old] if old else [])
    return _me_response(user)


@router.delete("/api/me/avatar")
def reset_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    old = user.avatar
    user.avatar = None
    db.commit()
    _remove_files([AVATARS_DIR / old] if old else [])
    return _me_response(user)


def _remove_files(paths):
    """storage 파일을 지운다. 프로필 사진을 바꾸거나 되돌릴 때 예전 파일도 지운다:
    users 행에는 지금 사진 이름만 남아, 예전 파일을 두면 회원 탈퇴 때 누구 것인지 찾아 지울 수 없다.
    서버가 만든 이름 형식만 지워, DB 값이 어긋나도 storage 밖이나 다른 종류의 파일은 건드리지 않는다.
    DB를 먼저 바꾼 뒤 부르므로, 파일을 지우지 못해도 요청은 성공으로 두고 서버 창에 남긴다"""
    for path in paths:
        if not SAFE_NAME.match(path.name):
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            log.warning("파일을 지우지 못했습니다: %s", path.name)


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
def change_password(body: PasswordBody, session: tuple[User, str] = Depends(current_session), db: Session = Depends(get_db)):
    user, token = session
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(400, "WRONG_PASSWORD", "지금 비밀번호가 올바르지 않습니다.")
    if not password_ok(body.new_password):
        raise ApiError(400, "INVALID_PASSWORD", "비밀번호는 8자 이상이고 숫자를 포함해야 합니다.")
    if body.new_password == body.current_password:
        raise ApiError(400, "SAME_PASSWORD", "지금 비밀번호와 다른 비밀번호를 입력해 주세요.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    revoke_other_tokens(db, user, token)  # 다른 기기에서 로그인한 것은 끊는다
    return {}


class WithdrawBody(BaseModel):
    password: str


def _user_files(db: Session, user: User):
    """이 회원의 storage 파일 경로. 이름은 모두 이 회원의 DB 행에서 얻으므로 예시 사진 원본과 다른 회원 파일은 들어가지 않는다.
    예시 사진을 고르면 화면이 사진을 새로 올려 이 회원의 images 행과 복사본 파일이 생기고, 지우는 것은 그 복사본이다"""
    uid = user.id
    paths = [AVATARS_DIR / user.avatar] if user.avatar else []
    for filename, thumb in db.execute(select(UploadedImage.filename, UploadedImage.thumb).where(UploadedImage.user_id == uid)):
        paths += [IMAGES_DIR / filename] + ([IMAGES_DIR / thumb] if thumb else [])
    for mask, cutout in db.execute(select(Extraction.mask, Extraction.cutout).where(Extraction.user_id == uid)):
        paths += [EXTRACTIONS_DIR / mask, EXTRACTIONS_DIR / cutout]  # cutout은 처음 열 때 만들므로 없을 수 있다
    result_ids = set(db.scalars(select(Result.result_id).where(Result.user_id == uid)))
    for area_mask, garment_mask, result_id in db.execute(select(Job.area_mask, Job.garment_mask, Job.result_id).where(Job.user_id == uid)):
        paths += [JOBS_DIR / area_mask] + ([JOBS_DIR / garment_mask] if garment_mask else [])
        if result_id:  # 24시간 정리로 results 행이 먼저 지워졌어도 파일이 남았으면 함께 지운다
            result_ids.add(result_id)
    for rid in result_ids:
        paths += [RESULTS_DIR / f"{rid}.png", RESULTS_DIR / f"{rid}_thumb.jpg"]
    return paths


@router.delete("/api/me")
def withdraw(body: WithdrawBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """회원 탈퇴. 지금 비밀번호를 다시 확인하고 이 회원의 DB 행과 storage 파일을 모두 지운다.
    대기·진행 중인 합성이 있으면 409 JOB_IN_PROGRESS (끝나면 일꾼이 결과를 새로 써 주인 없는 결과가 남으므로).
    지우는 순서: results → jobs → extractions → images → sessions → users, 한 트랜잭션.
    results의 사진 외래키가 사진 행 삭제를 막아 users만 지우고 CASCADE에 맡길 수 없다. 파일은 DB 삭제가 확정된 뒤 지운다"""
    if not verify_password(body.password, user.password_hash):
        raise ApiError(400, "WRONG_PASSWORD", "비밀번호가 올바르지 않습니다.")
    if compose.has_active_job(user.id):
        raise ApiError(409, "JOB_IN_PROGRESS", "진행 중인 합성이 끝난 뒤 다시 시도해 주세요.")
    uid = user.id
    paths = _user_files(db, user)
    for model, owner in ((Result, Result.user_id), (Job, Job.user_id), (Extraction, Extraction.user_id),
                         (UploadedImage, UploadedImage.user_id), (AuthSession, AuthSession.user_id), (User, User.id)):
        db.execute(delete(model).where(owner == uid))
    db.commit()
    compose.forget_user_jobs(uid)
    _remove_files(paths)
    return {}


@router.post("/api/auth/logout")
def logout(session: tuple[User, str] = Depends(current_session), db: Session = Depends(get_db)):
    revoke_token(db, session[1])
    return {}


@router.post("/api/auth/extend")
def extend(session: tuple[User, str] = Depends(current_session), db: Session = Depends(get_db)):
    # 이미 만료된 토큰은 current_session에서 401 → 연장 불가, 다시 로그인
    return {"expires_at": kst_text(extend_token(db, session[1]))}
