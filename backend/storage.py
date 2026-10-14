"""파일 저장소 도우미 (DB 대신 storage/ 폴더의 json으로 기록을 찾는다).

- 기록마다 user_id(만든 회원 번호)를 적고, 다른 회원의 기록은 "없음"(404)으로 답한다 (있는지 여부도 알리지 않음)
"""
import json
import re
from datetime import datetime, timedelta, timezone

from backend.config import EXTRACTIONS_DIR, IMAGES_DIR
from backend.errors import ApiError

KST = timezone(timedelta(hours=9))
_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def is_owner(record, user) -> bool:
    return record.get("user_id") == user.id


def _load(directory, item_id, code, message, user=None):
    """기록 읽기. user를 주면 그 회원 것이 아닐 때도 없는 것처럼 404"""
    if not isinstance(item_id, str) or not _ID.match(item_id):
        raise ApiError(404, code, message)
    path = directory / f"{item_id}.json"
    if not path.is_file():
        raise ApiError(404, code, message)
    record = json.loads(path.read_text(encoding="utf-8"))
    if user is not None and not is_owner(record, user):
        raise ApiError(404, code, message)
    return record


def load_image_info(image_id, user=None):
    """사진 올리기(3-1) 때 저장한 정보. 없거나 (user를 주면) 남의 것이면 404."""
    return _load(IMAGES_DIR, image_id, "IMAGE_NOT_FOUND", "사진을 찾을 수 없습니다. 다시 올려 주세요.", user)


def load_extraction_info(extraction_id, user=None):
    """상의 추출(4-1) 때 저장한 정보. 없거나 (user를 주면) 남의 것이면 404."""
    return _load(EXTRACTIONS_DIR, extraction_id, "EXTRACTION_NOT_FOUND", "추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.", user)
