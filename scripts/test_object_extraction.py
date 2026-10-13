"""UI 없이 객체 추출을 확인하는 스크립트.

예:
    python scripts/test_object_extraction.py Girl.jpg --points "487,731;483,443" --out girl_mask.png
"""
import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.object_extraction import extract_object


def parse_points(s):
    return [tuple(map(float, p.split(","))) for p in s.split(";") if p] if s else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--points", help="x1,y1;x2,y2")
    parser.add_argument("--neg", help="x1,y1;x2,y2")
    parser.add_argument("--box", help="x1,y1,x2,y2")
    parser.add_argument("--out", default="mask.png")
    args = parser.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(args.image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    box = tuple(map(float, args.box.split(","))) if args.box else None
    mask = extract_object(
        image_rgb,
        points=parse_points(args.points),
        neg_points=parse_points(args.neg),
        box=box,
    )

    cv2.imwrite(args.out, mask * 255)
    print("saved:", args.out, "| mask area:", round(mask.mean() * 100, 1), "%")


if __name__ == "__main__":
    main()
