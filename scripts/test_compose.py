"""서버·화면 없이 합성(AnyDoor)만 확인한다 (CGI 환경에서 실행).

사진 4장을 받아 합성하고 걸린 시간, 최대 GPU 메모리를 출력한다.
- 옷 사진, 옷 윤곽(흑백, 흰색 = 옷)
- 인물 사진, 입힐 영역(흑백, 흰색 = 입힐 곳)
결과: --out 파일 = 옷 사진 | 인물 사진 | 합성 결과

예 (저장소 맨 위 폴더에서):
    CGI\\Scripts\\python.exe scripts\\test_compose.py --garment cloth.jpg --garment-mask cloth_mask.png --person person.jpg --area area.png --out compose.jpg

옷 윤곽은 scripts/test_object_extraction.py로 만들 수 있다.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def read_rgb(path):
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def read_mask(path, size):
    """흑백 윤곽을 0/1로. 크기가 다르면 짝이 되는 사진 크기에 맞춘다"""
    mask = cv2.imread(str(path), 0)
    if mask is None:
        raise FileNotFoundError(path)
    if (mask.shape[1], mask.shape[0]) != size:
        mask = cv2.resize(mask, size, interpolation=cv2.INTER_NEAREST)
    mask = (mask > 127).astype(np.uint8)
    if mask.sum() == 0:
        raise ValueError(f"윤곽이 비어 있습니다 (흰색 부분 없음): {path}")
    return mask


def main():
    parser = argparse.ArgumentParser(description="AnyDoor 합성 확인")
    parser.add_argument("--garment", required=True, help="옷 사진")
    parser.add_argument("--garment-mask", required=True, help="옷 윤곽 (흑백 PNG, 흰색 = 옷)")
    parser.add_argument("--person", required=True, help="인물 사진")
    parser.add_argument("--area", required=True, help="입힐 영역 (흑백 PNG, 흰색 = 입힐 곳)")
    parser.add_argument("--out", default="compose.jpg", help="결과 파일 (옷 | 인물 | 합성)")
    parser.add_argument("--seed", type=int, default=1234, help="같은 seed면 같은 결과")
    args = parser.parse_args()

    import torch
    from features.composition import compose

    ref = read_rgb(args.garment)
    tar = read_rgb(args.person)
    ref_mask = read_mask(args.garment_mask, (ref.shape[1], ref.shape[0]))
    tar_mask = read_mask(args.area, (tar.shape[1], tar.shape[0]))

    shown = set()

    def on_progress(p):
        step = int(p * 10)
        if step not in shown:
            shown.add(step)
            print(f"  진행률 {p:.0%}", flush=True)

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats()
    gen = compose(ref, ref_mask, tar, tar_mask, seed=args.seed, on_progress=on_progress)
    print(f"합성(모델 불러오기 포함): {time.time() - t0:.0f}초, 최대 GPU 메모리 {torch.cuda.max_memory_allocated() / 1024 ** 3:.1f}GB")

    h, w = tar.shape[:2]
    panel = cv2.hconcat([cv2.resize(ref, (w, h)), tar, gen])
    cv2.imwrite(args.out, cv2.cvtColor(panel, cv2.COLOR_RGB2BGR))
    print(f"저장: {args.out}")


if __name__ == "__main__":
    main()
