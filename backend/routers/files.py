"""명세 7장 파일 보기: /api/files/{파일 이름}

- 주소에 붙은 열쇠(?key=)가 맞고 만료 전일 때만 보여 줌 (명세 7장 후보 1, 10/15 결정, backend/file_keys.py)
  - 열쇠는 서버가 사진 주소를 응답할 때 붙여 줌 → 화면은 받은 주소를 그대로 <img src>에 쓰면 됨
  - 열쇠가 없거나 틀리거나 만료면 없는 파일처럼 404
- 파일 이름은 서버가 만든 형식(img_xxxx.jpg 등)만 허용해 다른 폴더 파일을 열 수 없게 막는다
"""
import re

from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.config import FILE_DIRS
from backend.errors import ApiError
from backend.file_keys import check_key

router = APIRouter()
SAFE_NAME = re.compile(r"^[a-z]+_[0-9a-f]{12}(_[a-z]+)?\.(jpg|png)$")


@router.get("/api/files/{name}")
def get_file(name: str, key: str | None = None):
    # 열쇠가 없거나 틀리거나 만료되면 없는 파일처럼 404 (명세 7장)
    if not SAFE_NAME.match(name) or not check_key(name, key):
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    directory = FILE_DIRS.get(name.split("_", 1)[0])
    if directory is None:
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    path = directory / name
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    return FileResponse(path)
