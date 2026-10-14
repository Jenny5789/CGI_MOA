"""명세 5-3, 6-1, 6-2 합성 결과와 사진첩.

- GET   /api/results            : 결과 목록 (명세 6-1). 사진첩 탭, 내 작업 기록
- GET   /api/results/{id}       : 결과 하나 (명세 5-3)
- PATCH /api/results/{id}       : 저장 / 좋아요 (명세 6-2)
- 저장하지 않은 결과는 만든 지 3일 뒤 지운다 (명세 5-3, 10/12 결정). 목록을 볼 때 지난 것을 정리한다
- 임시: 로그인 확인 없음 → 모든 결과가 한 사람 것처럼 보임. 결과는 storage/results에 파일(json)로 저장
"""
import json
import threading
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import RESULT_KEEP_DAYS, RESULTS_DIR
from backend.errors import ApiError
from backend.storage import _ID, KST

router = APIRouter()
_lock = threading.Lock()  # 저장/좋아요를 동시에 바꿀 때 파일이 엉키지 않게

DETAIL_KEYS = ("result_id", "image_url", "thumb_url", "created_at", "saved", "favorite", "garment_image_id", "person_image_id")
LIST_KEYS = ("result_id", "thumb_url", "image_url", "created_at", "saved", "favorite")


def _path(result_id):
    if not isinstance(result_id, str) or not _ID.match(result_id) or not result_id.startswith("res_"):
        return None
    return RESULTS_DIR / f"{result_id}.json"


def _load(result_id):
    path = _path(result_id)
    if path is None or not path.is_file():
        raise ApiError(404, "RESULT_NOT_FOUND", "결과를 찾을 수 없습니다.")
    return json.loads(path.read_text(encoding="utf-8"))


def _all_records():
    if not RESULTS_DIR.is_dir():
        return []
    records = []
    for p in RESULTS_DIR.glob("res_*.json"):
        try:
            records.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue  # 쓰는 중이거나 깨진 파일은 건너뜀
    return records


def _remove_expired(records):
    """저장하지 않고 3일이 지난 결과를 지우고, 남은 것만 돌려준다"""
    limit = datetime.now(KST) - timedelta(days=RESULT_KEEP_DAYS)
    kept = []
    for r in records:
        if not r.get("saved") and datetime.fromisoformat(r["created_at"]) < limit:
            rid = r["result_id"]
            for name in (f"{rid}.png", f"{rid}_thumb.jpg", f"{rid}.json"):
                (RESULTS_DIR / name).unlink(missing_ok=True)
            continue
        kept.append(r)
    return kept


@router.get("/api/results")
def list_results(
    saved: Optional[bool] = None,
    favorite: Optional[bool] = None,
    date: Optional[str] = None,
    sort: Literal["new", "old"] = "new",
):
    with _lock:
        records = _remove_expired(_all_records())

    if date is not None:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ApiError(400, "INVALID_DATE", "날짜는 2026-10-14 같은 형식이어야 합니다.")

    counts = {
        "saved": sum(1 for r in records if r.get("saved")),
        "recent": sum(1 for r in records if not r.get("saved")),
        "favorite": sum(1 for r in records if r.get("favorite")),
    }
    items = records
    if saved is not None:
        items = [r for r in items if bool(r.get("saved")) == saved]
    if favorite is not None:
        items = [r for r in items if bool(r.get("favorite")) == favorite]
    if date is not None:
        # created_at은 한국 시간(+09:00)으로 저장되어 앞 10글자가 곧 한국 날짜 (명세 6-1)
        items = [r for r in items if r["created_at"][:10] == date]
    items = sorted(items, key=lambda r: r["created_at"], reverse=(sort == "new"))

    return {"items": [{k: r[k] for k in LIST_KEYS} for r in items], "counts": counts, "next_cursor": None}


@router.get("/api/results/{result_id}")
def get_result(result_id: str):
    record = _load(result_id)
    return {k: record[k] for k in DETAIL_KEYS}


class ResultPatch(BaseModel):
    saved: Optional[bool] = None
    favorite: Optional[bool] = None


@router.patch("/api/results/{result_id}")
def update_result(result_id: str, change: ResultPatch):
    if change.saved is None and change.favorite is None:
        raise ApiError(400, "INVALID_REQUEST", "saved 또는 favorite 중 하나를 보내 주세요.")
    with _lock:
        record = _load(result_id)
        if change.saved is not None:
            record["saved"] = change.saved
        if change.favorite is not None:
            record["favorite"] = change.favorite
        _path(result_id).write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return {k: record[k] for k in DETAIL_KEYS}
