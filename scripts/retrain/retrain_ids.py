"""AnyDoor 재학습 학습 쌍 목록 만들기 (+ 학습 재료 확인 그림).

- test: 시험 학습용 100쌍 = 학습용 무작위 3,000쌍(seed 1) 중 쓸 수 있는 쌍에서 짧은 상의 50 + 무작위 50 (10/24 시험과 같은 쌍)
- all : 학습용 전체에서 쓸 수 있는 쌍 모두 (본 학습용)
- 쓸 수 있는 쌍: retrain_dataset.usable (부위 지도 오류, 옷 마스크 오류, 관절 점 없음 제외)
- 저장: <out_dir>/ids.txt (한 줄 = 사진 번호, 그룹, 옷 아랫단 위치(목 = 0, 골반 = 1)), --samples면 train_samples.jpg (6쌍)

python retrain_ids.py <out_dir> test|all [--samples] [--workers N]
"""
import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from retrain_dataset import VI, make_item, usable  # noqa: E402

FONTS = [r"C:\Windows\Fonts\malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]


def font(size):
    from PIL import ImageFont

    for f in FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()  # 한글 글꼴이 없으면 기본 글꼴 (한글은 네모로 보일 수 있음)


def check(ids, workers):
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(usable, ids, chunksize=32))
    return {i: b for i, (ok, b) in zip(ids, res) if ok}


def draw_samples(rows_ids, cand, out):
    from PIL import Image, ImageDraw

    F, FB = font(15), font(18)
    S, GAP = 256, 8
    heads = ["참조 이미지 (224)", "정답 (512)", "조건 이미지 (512)", "생성 영역 (흰색 = 다시 그림)"]
    rows = []
    np.random.seed(0)
    for group, i in rows_ids:
        it = make_item(i)
        ims = [it["ref"] * 255, (it["jpg"] + 1) * 127.5, (it["hint"][:, :, :3] + 1) * 127.5,
               np.repeat((it["hint"][:, :, 3:] + 1) * 127.5, 3, -1)]
        r = Image.new("RGB", (4 * (S + GAP), S + 56), "white")
        dr = ImageDraw.Draw(r)
        dr.text((4, 2), f"{i} ({group}, 옷 아랫단 = 목~골반의 {cand[i] * 100:.0f}%)", fill="black", font=FB)
        for j, (t, a) in enumerate(zip(heads, ims)):
            dr.text((j * (S + GAP) + 2, 28), t, fill="black", font=F)
            r.paste(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((S, S)), (j * (S + GAP), 52))
        rows.append(r)
    sheet = Image.new("RGB", (rows[0].width, sum(x.height + 10 for x in rows)), "white")
    y = 0
    for x in rows:
        sheet.paste(x, (0, y))
        y += x.height + 10
    sheet.save(out, quality=90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("mode", choices=["test", "all"])
    ap.add_argument("--samples", action="store_true", help="학습 재료 확인 그림 저장 (6쌍)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ids = sorted(p.stem for p in (VI / "image").glob("*.jpg"))
    print(f"학습용 사진 {len(ids)}장 ({VI})", flush=True)
    if a.mode == "test":
        rng = np.random.default_rng(1)
        pool = [str(i) for i in rng.choice(ids, 3000, replace=False)]
        cand = check(pool, a.workers)
        ordered = [i for i in pool if i in cand]  # 고르는 순서를 10/24 시험과 같게
        short = sorted(ordered, key=lambda i: cand[i])[:50]
        rest = [i for i in ordered if i not in short]
        rand = [str(i) for i in rng.choice(rest, 50, replace=False)]
        lines = [f"{i}\tshort\t{cand[i]:.2f}" for i in short] + [f"{i}\trandom\t{cand[i]:.2f}" for i in rand]
        picks = [("짧은 상의", i) for i in short[:3]] + [("무작위", i) for i in rand[:3]]
    else:
        cand = check(ids, a.workers)
        lines = [f"{i}\tall\t{cand[i]:.2f}" for i in sorted(cand)]
        picks = [("전체", i) for i in sorted(cand)[:6]]
    (out / "ids.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"쓸 수 있는 쌍 {len(cand)}개 중 {len(lines)}쌍 → {out / 'ids.txt'}", flush=True)
    if a.samples:
        draw_samples(picks, cand, out / "train_samples.jpg")
        print("저장", out / "train_samples.jpg", flush=True)


if __name__ == "__main__":
    main()
