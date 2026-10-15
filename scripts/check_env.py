"""개발 환경 점검: 패키지 버전, GPU, 모델 가중치 파일, DB 설정 파일.

실행 (저장소 최상위 디렉터리): CGI\Scripts\python.exe scripts\check_env.py
기준 버전: docs/environment.md
"""
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    "torch": "2.5.1+cu121",
    "torchvision": "0.20.1+cu121",
    "numpy": "2.2.6",
    "xformers": "0.0.28.post3",
    "transformers": "5.14.1",
    "pytorch-lightning": "1.9.5",
    "SAM-2": None,  # 버전 고정 없음 (git 설치)
    "fastapi": "0.143.0",
    "uvicorn": "0.54.0",
    "SQLAlchemy": "2.0.54",
    "PyMySQL": None,
    "python-dotenv": "1.2.4",
}

FILES = {
    "SAM2 모델 가중치": ROOT / "checkpoints" / "sam2" / "sam2.1_hiera_base_plus.pt",
    "DB 접속 설정 (backend/.env)": ROOT / "backend" / ".env",
}

results = []


def check(name, ok, detail):
    results.append(ok)
    print(f"[{'OK' if ok else 'NG'}] {name}: {detail}")


check("Python", sys.version_info[:2] == (3, 10), sys.version.split()[0] + " (기준 3.10)")

for pkg, want in EXPECTED.items():
    try:
        got = version(pkg)
    except PackageNotFoundError:
        check(pkg, False, "설치 안 됨")
        continue
    check(pkg, want is None or got == want, got + ("" if want is None or got == want else f" (기준 {want})"))

try:
    import torch
    gpu = torch.cuda.is_available()
    check("GPU (CUDA)", gpu, torch.cuda.get_device_name(0) if gpu else "사용 불가")
except ImportError:
    check("GPU (CUDA)", False, "torch 없음")

anydoor = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor"))
check("AnyDoor 폴더", (anydoor / "run_inference.py").is_file(), str(anydoor))

for name, path in FILES.items():
    check(name, path.is_file(), str(path.relative_to(ROOT)))

print(f"\n결과: {sum(results)}/{len(results)} 통과")
sys.exit(0 if all(results) else 1)
