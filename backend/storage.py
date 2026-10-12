"""파일 저장소 도우미 (DB 대신 storage/ 폴더의 json으로 기록을 찾는다)."""
import json
import re
from datetime import datetime, timedelta, timezone

from backend.config import EXTRACTIONS_DIR, IMAGES_DIR
from backend.errors import ApiError

KST = timezone(timedelta(hours=9))
_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def _load(directory, item_id, code, message):
    if not isinstance(item_id, str) or not _ID.match(item_id):
        raise ApiError(404, code, message)
    path = directory / f"{item_id}.json"
    if not path.is_file():
        raise ApiError(404, code, message)
    return json.loads(path.read_text(encoding="utf-8"))


def load_image_info(image_id):
    """사진 올리기(3-1) 때 저장한 정보. 없으면 404."""
    return _load(IMAGES_DIR, image_id, "IMAGE_NOT_FOUND", "사진을 찾을 수 없습니다. 다시 올려 주세요.")


def load_extraction_info(extraction_id):
    """상의 추출(4-1) 때 저장한 정보. 없으면 404."""
    return _load(EXTRACTIONS_DIR, extraction_id, "EXTRACTION_NOT_FOUND", "추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.")
