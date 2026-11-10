"""서버 설정 (저장 위치, 제한 값)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 저장소 맨 위 폴더

# 이미지 파일을 두는 곳. 사진·추출 결과·작업·결과의 정보는 DB 표에 있고 여기에는 그림 파일만 둔다 (저장소에서는 제외)
STORAGE_DIR = ROOT / "storage"
IMAGES_DIR = STORAGE_DIR / "images"            # 올린 사진 (img_...)
EXTRACTIONS_DIR = STORAGE_DIR / "extractions"  # 추출 결과 윤곽·cutout 그림 (ext_...)
JOBS_DIR = STORAGE_DIR / "jobs"                # 합성 작업의 입힐 영역·다듬은 윤곽 그림 (job_...)
RESULTS_DIR = STORAGE_DIR / "results"          # 합성 결과 사진 (res_...)
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
RESULT_CLEANUP_SECONDS = 600  # 저장하지 않은 결과 정리(전체 회원)를 이 간격보다 자주 하지 않는다. 결과 목록 조회 때 확인하므로 정리가 최대 이 시간만큼 늦을 수 있음
RECENT_IMAGE_KEEP_HOURS = 24  # 합성하기 "최근 사용한 사진" 목록에 남기는 시간 (10/17, 올린 사진 기록 db.UploadedImage)
RECENT_IMAGE_LIMIT = 12       # 최근 사용한 사진 목록 최대 장수 (상의, 인물 사진 각각)

# 합성 후 원본 복원 후처리 (얼굴·머리·배경을 원본으로 되돌림, features/composition/restore.py). 끄기: MOA_RESTORE_ORIGINAL=0
RESTORE_ORIGINAL = os.environ.get("MOA_RESTORE_ORIGINAL", "1") != "0"

# 합성 후 박스 선 보정 (다시 그린 정사각형 테두리의 밝기·색을 원본에 맞춤, features/composition/seam.py). 끄기: MOA_SEAM_FIX=0
# 11/10부터 물체 기준 원본 복원은 배경을 원본으로 두므로, 원본 복원을 끄거나 사람을 찾지 못한 경우에만 적용
SEAM_FIX = os.environ.get("MOA_SEAM_FIX", "1") != "0"
