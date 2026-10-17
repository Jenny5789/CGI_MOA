"""화면 예시 생성 이미지를 웹용 JPG로 줄인다.

실행 (저장소 최상위 디렉터리): CGI\Scripts\python.exe scripts\compress_web_images.py
- 원본: generated_assets/<묶음>/*.png (1254x1254 PNG, 장당 약 2MB, 저장소에 올리지 않고 각자 보관)
- 결과: frontend/public/assets/generated/<묶음>/*.jpg (긴 변 1024px)
        합성하기 예시 묶음은 thumb/*.jpg도 만든다 (긴 변 240px, 예시 줄과 "더보기" 창에 보이는 작은 사진)
- 묶음 목록은 화면이 쓰는 것만 (frontend/src/data/generatedAssets.js와 맞춘다). 다시 실행하면 결과를 덮어쓴다.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "generated_assets"
OUT = ROOT / "frontend" / "public" / "assets" / "generated"

FULL_SIDE, FULL_QUALITY = 1024, 85
THUMB_SIDE, THUMB_QUALITY = 240, 80

# 묶음 이름: 작은 사진(thumb)도 만들지 여부
FOLDERS = {
    "tops_only_30": True,           # 합성하기 1단계 예시 (옷만 찍은 사진)
    "tops_worn_30": True,           # 합성하기 1단계 예시 (사람이 입은 사진)
    "base_models_30": True,         # 합성하기 2단계 예시 (상반신)
    "full_body_models_30": True,    # 합성하기 2단계 예시 (전신)
    "showcase_tops_30": False,      # 홈 위쪽 예시: 상의
    "curated_backgrounds_8": False,  # 홈 위쪽 예시: 인물
    "curated_results_8": False,     # 홈 위쪽 예시: 합성 결과
    "feature_lifestyle_3": False,   # 홈 기능 소개 사진
}


def save_jpg(img, side, quality, path):
    img = img.copy()
    img.thumbnail((side, side), Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path.stat().st_size


def main():
    total_src = total_out = count = 0
    for folder, make_thumb in FOLDERS.items():
        pngs = sorted((SRC / folder).glob("*.png"))
        if not pngs:
            print(f"[없음] {SRC / folder}")
            return 1
        src_bytes = out_bytes = 0
        for png in pngs:
            with Image.open(png) as im:
                img = im.convert("RGB")
            src_bytes += png.stat().st_size
            out_bytes += save_jpg(img, FULL_SIDE, FULL_QUALITY, OUT / folder / f"{png.stem}.jpg")
            if make_thumb:
                out_bytes += save_jpg(img, THUMB_SIDE, THUMB_QUALITY, OUT / folder / "thumb" / f"{png.stem}.jpg")
        print(f"{folder:24s} {len(pngs):3d}장  {src_bytes / 1e6:7.1f}MB -> {out_bytes / 1e6:6.1f}MB")
        total_src += src_bytes
        total_out += out_bytes
        count += len(pngs)
    print(f"{'합계':24s} {count:3d}장  {total_src / 1e6:7.1f}MB -> {total_out / 1e6:6.1f}MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
