"""명세 5-3, 6-1, 6-2 합성 결과와 사진첩.

- GET   /api/results            : 결과 목록 (명세 6-1). 사진첩 탭, 내 작업 기록
- GET   /api/results/{id}       : 결과 하나 (명세 5-3)
- PATCH /api/results/{id}       : 저장 / 좋아요 (명세 6-2)
- GET   /api/results/{id}/source: 결과를 만든 재료 (명세 외 추가 제안). 합성하기 "내 작업 기록"에서 결과를 열 때 1~4단계를 채운다
- 저장하지 않은 결과는 만든 지 24시간 뒤 지운다 (명세 5-3, 10/16 결정: 3일 → 24시간). 목록을 볼 때 지난 것을 정리한다
- 로그인 필요. 자기 결과만 보이고 바꿀 수 있음 (남의 결과는 404). 결과 정보는 DB results 표(11/2), 결과 사진은 storage/results에 파일로 저장
- 사진 주소(image_url, thumb_url)는 응답할 때 열쇠를 붙여 줌 (명세 7장, backend/file_keys.py). 사진 파일 이름은 결과 번호에서 만든다 (res_xxx.png, res_xxx_thumb.jpg)
- DB는 시각을 UTC로 저장한다. 응답의 created_at과 날짜(date) 필터는 예전처럼 한국 시간 기준
"""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.auth import current_user
from backend.config import EXTRACTIONS_DIR, JOBS_DIR, RESULT_KEEP_HOURS, RESULTS_DIR
from backend.db import Result, User, get_db, utcnow
from backend.errors import ApiError
from backend.file_keys import signed_url
from backend.storage import _ID, KST, load_extraction_info, load_image_info, load_job_info

router = APIRouter()

DETAIL_KEYS = ("result_id", "image_url", "thumb_url", "created_at", "saved", "favorite", "garment_image_id", "person_image_id")
LIST_KEYS = ("result_id", "thumb_url", "image_url", "created_at", "saved", "favorite")


def _public(row, keys):
    """응답할 칸만 골라, 사진 주소에 열쇠를 붙인다 (사진 파일 이름은 결과 번호에서 만듦). created_at은 한국 시간 글자로"""
    values = {
        "result_id": row.result_id,
        "image_url": signed_url(f"{row.result_id}.png"),
        "thumb_url": signed_url(f"{row.result_id}_thumb.jpg"),
        "created_at": row.created_at.replace(tzinfo=timezone.utc).astimezone(KST).isoformat(timespec="seconds"),
        "saved": row.saved,
        "favorite": row.favorite,
        "garment_image_id": row.garment_image_id,
        "person_image_id": row.person_image_id,
    }
    return {k: values[k] for k in keys}


def _load(db, result_id, user):
    if not isinstance(result_id, str) or not _ID.match(result_id) or not result_id.startswith("res_"):
        raise ApiError(404, "RESULT_NOT_FOUND", "결과를 찾을 수 없습니다.")
    row = db.get(Result, result_id)
    if row is None or row.user_id != user.id:  # 남의 결과도 없는 것처럼
        raise ApiError(404, "RESULT_NOT_FOUND", "결과를 찾을 수 없습니다.")
    return row


def _remove_expired(db):
    """저장하지 않고 24시간이 지난 결과를 (모든 회원 것을 함께) 지운다: DB 행을 먼저, 실제로 지워진 것의 사진 파일을 그다음에.
    행을 지울 때도 같은 조건을 다시 걸어서, 고르는 사이에 "저장"이 눌린 결과는 지우지 않는다"""
    limit = utcnow() - timedelta(hours=RESULT_KEEP_HOURS)
    ids = db.scalars(select(Result.result_id).where(Result.saved.is_(False), Result.created_at < limit)).all()
    if not ids:
        return
    db.execute(delete(Result).where(Result.result_id.in_(ids), Result.saved.is_(False), Result.created_at < limit))
    db.commit()
    still = set(db.scalars(select(Result.result_id).where(Result.result_id.in_(ids))))
    for rid in ids:
        if rid not in still:
            for name in (f"{rid}.png", f"{rid}_thumb.jpg"):
                (RESULTS_DIR / name).unlink(missing_ok=True)


@router.get("/api/results")
def list_results(
    saved: Optional[bool] = None,
    favorite: Optional[bool] = None,
    date: Optional[str] = None,
    sort: Literal["new", "old"] = "new",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _remove_expired(db)  # 24시간 지난 것은 모든 회원 것을 함께 정리

    if date is not None:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ApiError(400, "INVALID_DATE", "날짜는 2026-10-14 같은 형식이어야 합니다.")

    mine = Result.user_id == user.id
    groups = db.execute(select(Result.saved, Result.favorite, func.count()).where(mine).group_by(Result.saved, Result.favorite)).all()
    counts = {
        "saved": sum(n for is_saved, _, n in groups if is_saved),
        "recent": sum(n for is_saved, _, n in groups if not is_saved),
        "favorite": sum(n for is_saved, is_fav, n in groups if is_saved and is_fav),  # 사진첩(저장한 결과)의 좋아요 탭
    }

    query = select(Result).where(mine)
    if saved is not None:
        query = query.where(Result.saved == saved)
    if favorite is not None:
        query = query.where(Result.favorite == favorite)
    if date is not None:
        # 한국 날짜 하루(명세 6-1)를 UTC 구간으로 바꿔 비교: 한국 0시 = 전날 UTC 15시
        start = day - timedelta(hours=9)
        query = query.where(Result.created_at >= start, Result.created_at < start + timedelta(days=1))
    order = Result.created_at.desc() if sort == "new" else Result.created_at.asc()
    rows = db.scalars(query.order_by(order, Result.result_id)).all()

    return {"items": [_public(r, LIST_KEYS) for r in rows], "counts": counts, "next_cursor": None}


@router.get("/api/results/{result_id}")
def get_result(result_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _public(_load(db, result_id, user), DETAIL_KEYS)


@router.get("/api/results/{result_id}/source")
def get_result_source(result_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """결과를 만든 재료: 상의·인물 사진, 상의 윤곽(다듬은 것, 없으면 SAM2 것), 입힐 영역, 합성 설정.
    재료 파일 중 하나라도 없으면 404 SOURCE_NOT_FOUND (화면은 결과만 보여 준다)"""
    row = _load(db, result_id, user)
    missing = ApiError(404, "SOURCE_NOT_FOUND", "이 결과의 재료를 찾을 수 없습니다.")
    if row.job_id is None or row.extraction_id is None:  # 연결된 작업·추출 결과가 지워져 비어 있음
        raise missing
    try:
        job = load_job_info(row.job_id)
        ext = load_extraction_info(row.extraction_id, user)
        garment = load_image_info(row.garment_image_id, user)
        person = load_image_info(row.person_image_id, user)
    except ApiError:
        raise missing
    garment_mask = (JOBS_DIR / job["garment_mask"]) if job.get("garment_mask") else (EXTRACTIONS_DIR / ext["mask"])
    area_mask = JOBS_DIR / job["area_mask"]
    if not garment_mask.is_file() or not area_mask.is_file():
        raise missing

    def image(info):
        return {"image_id": info["image_id"], "url": signed_url(info["filename"]), "width": info["width"], "height": info["height"]}

    return {
        "result_id": result_id,
        "garment": image(garment),
        "person": image(person),
        "extraction_id": row.extraction_id,
        "garment_mask_url": signed_url(garment_mask.name),
        "area_mask_url": signed_url(area_mask.name),
        "refine": bool(job.get("refine", False)),
        "shape_control": bool(job.get("shape_control", False)),
    }


class ResultPatch(BaseModel):
    saved: Optional[bool] = None
    favorite: Optional[bool] = None


@router.patch("/api/results/{result_id}")
def update_result(result_id: str, change: ResultPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if change.saved is None and change.favorite is None:
        raise ApiError(400, "INVALID_REQUEST", "saved 또는 favorite 중 하나를 보내 주세요.")
    row = _load(db, result_id, user)
    if change.saved is not None:  # 바뀐 칸만 갱신되므로 저장과 좋아요를 동시에 눌러도 서로 덮어쓰지 않음
        row.saved = change.saved
    if change.favorite is not None:
        row.favorite = change.favorite
    db.commit()
    return _public(row, DETAIL_KEYS)
