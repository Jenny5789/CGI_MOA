"""서버 설정 (저장 위치, 제한 값)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 저장소 맨 위 폴더

# 올린 사진과 결과 파일을 두는 곳 (DB 대신 파일로 저장, 저장소에서는 제외)
STORAGE_DIR = ROOT / "storage"
IMAGES_DIR = STORAGE_DIR / "images"            # 올린 사진 (img_...)
EXTRACTIONS_DIR = STORAGE_DIR / "extractions"  # 추출 결과 (ext_...)
JOBS_DIR = STORAGE_DIR / "jobs"                # 합성 작업 기록, 입힐 영역 (job_...)
RESULTS_DIR = STORAGE_DIR / "results"          # 합성 결과 (res_...)
AVATARS_DIR = STORAGE_DIR / "avatars"          # 프로필 사진 (avt_...)

# /api/files 로 보여 줄 파일: 이름 앞부분으로 폴더를 고른다
FILE_DIRS = {"img": IMAGES_DIR, "ext": EXTRACTIONS_DIR, "res": RESULTS_DIR, "job": JOBS_DIR,  # job: 입힐 영역·다듬은 윤곽 (작업 기록 불러오기)
             "avt": AVATARS_DIR}
AVATAR_SIDE = 256  # 프로필 사진은 가운데를 정사각형으로 잘라 이 크기로 저장

# 명세 3-1: 10MB 이하, jpg/png
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}
IMAGE_KINDS = {"garment", "person"}

# 명세 5-3: 저장하지 않은 합성 결과를 남겨 두는 시간 (10/12 3일 → 10/16 24시간)
RESULT_KEEP_HOURS = 24
RECENT_IMAGE_KEEP_HOURS = 24  # 합성하기 "최근 사용한 사진" 목록에 남기는 시간 (10/17, 올린 사진 기록 db.UploadedImage)
RECENT_IMAGE_LIMIT = 12       # 최근 사용한 사진 목록 최대 장수 (상의, 인물 사진 각각)

# 합성 후 원본 복원 후처리 (얼굴·머리·배경을 원본으로 되돌림, features/composition/restore.py). 끄기: MOA_RESTORE_ORIGINAL=0
RESTORE_ORIGINAL = os.environ.get("MOA_RESTORE_ORIGINAL", "1") != "0"

# 합성 후 박스 선 보정 (다시 그린 정사각형 테두리의 밝기·색을 원본에 맞춤, features/composition/seam.py). 끄기: MOA_SEAM_FIX=0
SEAM_FIX = os.environ.get("MOA_SEAM_FIX", "1") != "0"
