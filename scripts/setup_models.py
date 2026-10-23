"""AI 모델 준비: AnyDoor 코드 받기, 모델 가중치 3개 다운로드, AnyDoor 설정 파일 경로 수정.

실행 (저장소 최상위 디렉터리, conda 환경 CGI): python scripts\\setup_models.py
- 다시 실행해도 안전: 크기가 맞는 파일은 건너뛰고, 중단된 다운로드는 이어 받음
- 설치 순서: README 9. 설치 및 실행, 설치 5
"""
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANYDOOR = ROOT / "checkpoints" / "AnyDoor"
ANYDOOR_REPO = "https://github.com/ali-vilab/AnyDoor"
ANYDOOR_COMMIT = "44ca2b2"  # 합성 모듈이 run_inference.py의 정해진 줄을 바꿔 실행하므로 고정

MODELS = [  # 이름, 저장 위치, 주소, 바이트 수
    ("SAM2 가중치", ROOT / "checkpoints" / "sam2" / "sam2.1_hiera_base_plus.pt",
     "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt", 323_606_802),
    ("AnyDoor 가중치", ANYDOOR / "checkpoints" / "epoch=1-step=8687.ckpt",
     "https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch%3D1-step%3D8687.ckpt", 16_836_620_171),
    ("DINOv2 가중치", ANYDOOR / "checkpoints" / "dinov2_vitg14_pretrain.pth",
     "https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth", 4_546_108_579),
]

CONFIG_FIXES = [  # 공식 설정의 path/... 자리표시 경로를 받은 가중치 위치로
    (ANYDOOR / "configs" / "inference.yaml", "path/epoch=1-step=8687.ckpt", "./checkpoints/epoch=1-step=8687.ckpt"),
    (ANYDOOR / "configs" / "anydoor.yaml", "path/dinov2_vitg14_pretrain.pth", "checkpoints/dinov2_vitg14_pretrain.pth"),
]


def get_anydoor():
    if (ANYDOOR / "run_inference.py").is_file():
        print(f"[건너뜀] AnyDoor 코드: {ANYDOOR}")
        return
    print("[받는 중] AnyDoor 코드")
    subprocess.run(["git", "clone", ANYDOOR_REPO, str(ANYDOOR)], check=True)
    subprocess.run(["git", "-C", str(ANYDOOR), "checkout", "-q", ANYDOOR_COMMIT], check=True)


def download(name, path, url, size):
    if path.is_file() and path.stat().st_size == size:
        print(f"[건너뜀] {name}: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    done = part.stat().st_size if part.is_file() else 0
    req = urllib.request.Request(url, headers={"Range": f"bytes={done}-"} if done else {})
    with urllib.request.urlopen(req) as res:
        if done and res.status != 206:  # 이어 받기 미지원 응답이면 처음부터
            done = 0
        with open(part, "ab" if done else "wb") as f:
            while chunk := res.read(8 << 20):
                f.write(chunk)
                done += len(chunk)
                print(f"\r[받는 중] {name}: {done / size:6.1%}  {done / 2**30:.2f} / {size / 2**30:.2f} GiB", end="", flush=True)
    print()
    if part.stat().st_size != size:
        sys.exit(f"[실패] {name}: 크기 불일치 {part.stat().st_size:,} / {size:,}바이트. 다시 실행하면 이어 받음")
    part.replace(path)


def fix_configs():
    for path, old, new in CONFIG_FIXES:
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new), encoding="utf-8")
            print(f"[수정] {path.name}: {new}")
        elif new in text:
            print(f"[건너뜀] {path.name}: 수정 완료 상태")
        else:
            sys.exit(f"[실패] {path.name}: 수정할 경로 없음. AnyDoor 커밋 {ANYDOOR_COMMIT} 확인")


if __name__ == "__main__":
    get_anydoor()
    for m in MODELS:
        download(*m)
    fix_configs()
    print("결과: AI 모델 준비 완료")
