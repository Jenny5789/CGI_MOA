"""README 그림 원본(HTML)을 PNG로 만든다.

사용법 (저장소 최상위 폴더에서)
    python docs/readme/src/render.py                 세 그림 모두 다시 생성
    python docs/readme/src/render.py erd             하나만 생성 (architecture, erd, flow)
    python docs/readme/src/render.py --out-dir 폴더   저장소 그림을 덮어쓰지 않고 다른 폴더에 생성

필요한 것: Google Chrome, Pillow, Windows 글꼴 맑은 고딕 (HTML이 이 글꼴을 사용)
Chrome 위치가 다르면 환경 변수 CHROME에 실행 파일 경로를 지정한다.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

SRC = Path(__file__).resolve().parent

# 이름: (원본 HTML, 결과 PNG, 창 높이). 창 높이는 그림보다 크기만 하면 된다 (남는 아래쪽은 잘라 냄)
TARGETS = {
    "architecture": ("architecture.html", "moa_system_architecture.png", 1000),
    "erd": ("erd.html", "moa_erd.png", 1400),
    "flow": ("flow.html", "moa_flow.png", 1000),
}

BEIGE = (244, 242, 238)  # 그림 바탕색. 아래쪽 흰 여백이 어디서 시작하는지 찾는 기준
SCALE = 3                # 3배 크기로 찍은 뒤 너비 OUT_WIDTH로 줄여 글자를 선명하게 함
OUT_WIDTH = 2400


def find_chrome():
    candidates = [os.environ.get("CHROME"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
    for path in candidates:
        if path and Path(path).exists():
            return path
    for name in ("chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Chrome을 찾지 못했습니다. 환경 변수 CHROME에 chrome.exe 경로를 지정하세요.")


def capture(chrome, html, height, raw):
    # ERD · 흐름도는 스크립트가 선과 카드를 그리므로 그리기가 끝날 때까지 기다린 뒤 찍는다
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--force-device-scale-factor={SCALE}", f"--window-size=1200,{height}",
            "--virtual-time-budget=5000", f"--user-data-dir={profile}",
            f"--screenshot={raw}", html.as_uri(),
        ], check=True, capture_output=True)
    if not raw.exists():
        sys.exit(f"캡처 실패: {html.name}")


def crop_and_resize(raw, dst):
    im = Image.open(raw).convert("RGB")
    width, height = im.size
    # 아래에서 위로 올라가며 그림 바탕색이 처음 나오는 줄을 찾아 그 아래 흰 여백을 자른다
    last = height - 1
    while last > 0 and im.getpixel((width // 2, last)) != BEIGE and im.getpixel((8, last)) != BEIGE:
        last -= 1
    im = im.crop((0, 0, width, last + 1))
    im = im.resize((OUT_WIDTH, round(im.size[1] * OUT_WIDTH / im.size[0])), Image.LANCZOS)
    im.save(dst, optimize=True)
    return im.size


def main():
    parser = argparse.ArgumentParser(description="README 그림 원본(HTML)을 PNG로 생성")
    parser.add_argument("names", nargs="*", help="architecture, erd, flow (생략하면 모두)")
    parser.add_argument("--out-dir", type=Path, default=SRC.parent, help="결과 PNG 폴더 (기본: docs/readme)")
    args = parser.parse_args()

    names = args.names or list(TARGETS)
    for name in names:
        if name not in TARGETS:
            sys.exit(f"알 수 없는 이름: {name} (architecture, erd, flow 중 선택)")

    chrome = find_chrome()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work:
        for name in names:
            html_name, png_name, height = TARGETS[name]
            raw = Path(work) / f"{name}_raw.png"
            capture(chrome, SRC / html_name, height, raw)
            size = crop_and_resize(raw, args.out_dir / png_name)
            print(f"{png_name}: {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
