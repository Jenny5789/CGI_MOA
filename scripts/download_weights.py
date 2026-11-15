"""MOA 실행에 필요한 가중치 3개를 내려받아 checkpoints 폴더에 놓는다.

- 이미지 합성: AnyDoor 추가 학습 가중치 mix35000_fp16.ckpt, Hugging Face 모델 저장소
- 이미지 분할: SAM 2.1 Hiera Base+, Meta 공식 배포 주소
- 초해상도: Real-ESRGAN x2plus, 공식 GitHub 릴리스 v0.2.1
- 받은 파일은 크기와 SHA-256으로 확인하고, 이미 맞는 파일이 있으면 건너뜀
- 끊긴 다운로드는 .part 파일에서 이어 받음
- Python 표준 라이브러리만 사용. Docker만 있는 PC는 local/docker-compose.yml의 weights 서비스로 실행

사용:
    python scripts/download_weights.py
    python scripts/download_weights.py --repo <Hugging Face 저장소 이름> --dest <폴더>
환경 변수:
    MOA_WEIGHTS_REPO  합성 가중치 Hugging Face 저장소 이름, --repo와 같음
    HF_TOKEN          동의 후 받기로 설정한 저장소일 때 Hugging Face 읽기 토큰
"""
import argparse
import hashlib
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# 합성 가중치를 올린 Hugging Face 모델 저장소
DEFAULT_REPO = os.environ.get("MOA_WEIGHTS_REPO") or "JI-SEOP/moa-anydoor-mix35000"

ROOT = Path(__file__).resolve().parents[1]

# 저장 위치는 model_server/docker-compose.yml과 local/docker-compose.yml의 기본 연결 폴더와 같음
FILES = [
    {
        "name": "이미지 합성 가중치",
        "path": "weights/mix35000_fp16.ckpt",
        "hf_file": "mix35000_fp16.ckpt",
        "size": 4904383398,
        "sha256": "c0e48d1b93df66c6b4c840bb2d049b5399bc27baabb286930a42897339c2c683",
    },
    {
        "name": "SAM2 가중치",
        "path": "sam2/sam2.1_hiera_base_plus.pt",
        "url": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt",
        "size": 323606802,
        "sha256": "a2345aede8715ab1d5d31b4a509fb160c5a4af1970f199d9054ccfb746c004c5",
    },
    {
        "name": "초해상도 가중치",
        "path": "realesrgan/RealESRGAN_x2plus.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "size": 67061725,
        "sha256": "49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb",
    },
]

CHUNK = 1024 * 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Hugging Face 토큰을 파일 저장 서버로 넘기지 않도록 첫 이동 주소만 받아 옴"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK * 8), b""):
            h.update(block)
    return h.hexdigest()


def resolve_url(url, token):
    """토큰이 필요한 주소는 첫 응답의 이동 주소를 받아, 이후 요청은 토큰 없이 보냄"""
    if not token:
        return url
    req = urllib.request.Request(url, method="HEAD", headers={"Authorization": f"Bearer {token}"})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60):
            return url
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            return urllib.parse.urljoin(url, e.headers["Location"])
        if e.code in (401, 403):
            raise SystemExit("Hugging Face 저장소 접근 거부: 저장소 페이지에서 이용 조건에 동의했는지, HF_TOKEN이 맞는지 확인")
        raise


def download(url, dest, size, sha256, token=None):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    url = resolve_url(url, token)

    done = part.stat().st_size if part.exists() else 0
    if done > size:
        part.unlink()
        done = 0
    headers = {"User-Agent": "moa-download-weights"}
    if done:
        headers["Range"] = f"bytes={done}-"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 416 and done == size:
            resp = None
        else:
            raise
    if resp is not None:
        with resp:
            # 이어 받기를 지원하지 않는 서버는 처음부터 다시 보냄
            mode = "ab" if done and resp.status == 206 else "wb"
            if mode == "wb":
                done = 0
            start, last = time.time(), 0.0
            with open(part, mode) as f:
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    f.write(block)
                    done += len(block)
                    now = time.time()
                    if now - last > 1 or done == size:
                        rate = done / max(now - start, 1e-6) / CHUNK
                        print(f"\r  {done / size * 100:5.1f}%  {done // CHUNK:,} / {size // CHUNK:,} MB  {rate:5.1f} MB/s", end="", flush=True)
                        last = now
            print()
    got = part.stat().st_size
    if got != size:
        raise SystemExit(f"  크기 불일치: {got:,} / {size:,}바이트. 다시 실행하면 이어 받음")
    print("  SHA-256 확인 중")
    digest = sha256_of(part)
    if digest != sha256:
        part.unlink()
        raise SystemExit(f"  SHA-256 불일치: {digest}. 받은 파일을 지웠으니 다시 실행")
    os.replace(part, dest)


def main():
    ap = argparse.ArgumentParser(description="MOA 가중치 내려받기")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="합성 가중치 Hugging Face 저장소 이름, 예: 사용자이름/저장소이름")
    ap.add_argument("--dest", default=str(ROOT / "checkpoints"), help="저장 폴더, 기본 저장소의 checkpoints")
    ap.add_argument("--verify", action="store_true", help="이미 있는 파일도 SHA-256까지 확인")
    args = ap.parse_args()
    token = os.environ.get("HF_TOKEN") or None

    dest_root = Path(args.dest)
    print(f"저장 폴더: {dest_root}")
    for item in FILES:
        target = dest_root / item["path"]
        print(f"\n[{item['name']}] {item['path']}")
        if target.exists() and target.stat().st_size == item["size"]:
            if not args.verify or sha256_of(target) == item["sha256"]:
                print("  이미 있음, 건너뜀")
                continue
            print("  SHA-256 불일치, 다시 받음")
        if "url" in item:
            url, tok = item["url"], None
        else:
            if not args.repo:
                raise SystemExit("  합성 가중치 저장소 이름 없음: --repo 또는 환경 변수 MOA_WEIGHTS_REPO 지정")
            url = f"https://huggingface.co/{args.repo}/resolve/main/{item['hf_file']}"
            tok = token
        download(url, target, item["size"], item["sha256"], tok)
        print("  완료")
    print("\n가중치 준비 완료")


if __name__ == "__main__":
    sys.exit(main())
