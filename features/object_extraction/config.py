"""SAM2 설정. 경로는 환경변수로 덮어쓸 수 있다."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# SAM2 체크포인트 (.pt). 저장소에는 포함하지 않는다 (.gitignore).
SAM2_CHECKPOINT = os.environ.get(
    "SAM2_CHECKPOINT",
    str(PROJECT_ROOT / "checkpoints" / "sam2" / "sam2.1_hiera_base_plus.pt"),
)

# sam2 패키지 내부 config 이름
SAM2_CONFIG = os.environ.get("SAM2_CONFIG", "configs/sam2.1/sam2.1_hiera_b+.yaml")

# "cuda" / "cpu". 비우면 자동 선택
SAM2_DEVICE = os.environ.get("SAM2_DEVICE", "")
