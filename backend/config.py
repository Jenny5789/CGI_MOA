"""서버 설정 (저장 위치, 제한 값)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 저장소 맨 위 폴더

# 올린 사진과 결과 파일을 두는 곳 (DB 대신 파일로 저장, 저장소에서는 제외)
STORAGE_DIR = ROOT / "storage"
IMAGES_DIR = STORAGE_DIR / "images"            # 올린 사진 (img_...)
EXTRACTIONS_DIR = STORAGE_DIR / "extractions"  # 추출 결과 (ext_...)
JOBS_DIR = STORAGE_DIR / "jobs"                # 합성 작업 기록, 입힐 영역 (job_...)
RESULTS_DIR = STORAGE_DIR / "results"          # 합성 결과 (res_...)

# /api/files 로 보여 줄 파일: 이름 앞부분으로 폴더를 고른다
FILE_DIRS = {"img": IMAGES_DIR, "ext": EXTRACTIONS_DIR, "res": RESULTS_DIR}

# 명세 3-1: 10MB 이하, jpg/png
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}
IMAGE_KINDS = {"garment", "person"}

# 명세 5-3 (10/12 결정): 저장하지 않은 합성 결과를 남겨 두는 기간
RESULT_KEEP_DAYS = 3
