"""명세 7장 파일 보기: /api/files/{파일 이름}

- 임시: 누구나 볼 수 있음. 본인 것만 보이게 하는 방식은 명세 7장에서 미정 (서버 담당자와 결정)
- 파일 이름은 서버가 만든 형식(img_xxxx.jpg 등)만 허용해 다른 폴더 파일을 열 수 없게 막는다
"""
import re

from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.config import FILE_DIRS
from backend.errors import ApiError

router = APIRouter()
SAFE_NAME = re.compile(r"^[a-z]+_[0-9a-f]{12}(_[a-z]+)?\.(jpg|png)$")


@router.get("/api/files/{name}")
def get_file(name: str):
    if not SAFE_NAME.match(name):
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    directory = FILE_DIRS.get(name.split("_", 1)[0])
    if directory is None:
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    path = directory / name
    if not path.is_file():
        raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없습니다.")
    return FileResponse(path)
