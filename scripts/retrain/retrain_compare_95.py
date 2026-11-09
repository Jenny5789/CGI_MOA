"""AnyDoor 재학습 결과 확인 (95장): 여러 가중치를 같은 새 입력·같은 seed로 합성해 비교, 박스 선 보정(포아송) 전후 측정.

- 대상: VITON-HD 시험용 95쌍 (pairs_95.json: 인물 사진, 새 상의 사진, seed, 2026-10-17 시험과 같은 쌍)
- 합성: 서버 features.composition.AnyDoorComposer 그대로 (float16, save_memory, 크롭 1.3배, 50스텝), process_pairs만 새 입력으로 교체
  - 생성 영역 = agnostic-mask (상체 + 팔) + 원래 상의 (상의 라벨 5px 넓힘, 학습 재료와 같음)
  - 조건 이미지 = 옷 사진 비율 그대로 어깨 기준 배치 (VITON-HD 관절 점)
- 가중치: 이름=경로 여러 개, 경로가 original이면 AnyDoor 공식 가중치 ($ANYDOOR_DIR/checkpoints/epoch=1-step=8687.ckpt)
- 박스 선 보정: 저장소 features.composition.fix_seam (앱 서버와 같음), 원본 복원은 안 붙임
- 숫자 (가중치마다): 박스 선 세기 포아송 전·후 (다시 그린 정사각형 테두리 안팎 밝기 차이의 가운데값, 0 = 선 없음),
  바뀌면 안 되는 곳의 밝기 변화 (정사각형 안이면서 생성 영역 10px 밖의 평균 밝기 차이, 음수 = 어두워짐)
- 이미 만든 결과는 건너뜀, --limit N이면 앞의 N쌍만 (동작 확인용)
- 저장: <out_dir>/V??_seed????_<이름>.png, compare/V??.jpg (한 쌍씩), overview_?.jpg (12쌍씩), compare_95.csv,
        --pick V02,V08,...이면 compare_pick.jpg (고른 사진만 모음)

python retrain_compare_95.py <out_dir> original=original aug10000=<가중치 .ckpt> noaug10000=<가중치 .ckpt> [--pick V02,V08] [--limit 2]
경로: ANYDOOR_DIR (AnyDoor 폴더), VITON_TEST_DIR (기본 $ANYDOOR_DIR/data/zalando-hd-resized/test)
"""
import argparse
import csv
import gc
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # 저장소 최상위 (features 패키지)
sys.path.insert(1, str(HERE))
import cv2  # noqa: E402

from retrain_dataset import AD, DIL, UPPER, inference_item, server_crop  # noqa: E402
from retrain_ids import font  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out_dir")
ap.add_argument("weights", nargs="+", help="이름=가중치 경로 (경로가 original이면 공식 가중치)")
ap.add_argument("--pick", default="", help="고른 사진 번호 (예: V02,V08), compare_pick.jpg로 모음")
ap.add_argument("--limit", type=int, default=0, help="앞의 N쌍만 (0이면 95쌍 모두)")
a = ap.parse_args()

W = []
for w in a.weights:
    if "=" not in w:
        sys.exit(f"가중치는 이름=경로 형식: {w}")
    name, path = w.split("=", 1)
    W.append((name, path))
OUT = Path(a.out_dir)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "compare").mkdir(exist_ok=True)
VT = Path(os.environ.get("VITON_TEST_DIR", AD / "data" / "zalando-hd-resized" / "test"))
OFFICIAL = AD / "checkpoints" / "epoch=1-step=8687.ckpt"
M, KEEP_DIL = 5, 10  # crop_back 테두리, 밝기 측정에서 뺄 생성 영역 둘레 (px). 크롭 배율은 서버와 같은 retrain_dataset.SERVER_CROP
TW, TH, GAP = 200, 267, 8  # 쌍별 비교 그림 한 칸 (px)
CW, CH, COLS, PER = 150, 200, 2, 12  # 모음 그림: 한 칸 크기, 열 수, 한 장에 넣는 쌍 수
LUM = np.array([0.299, 0.587, 0.114], np.float32)
NA = "측정 불가"
pairs = list(enumerate(json.loads((HERE / "pairs_95.json").read_text(encoding="utf-8")), 1))
if a.limit:
    pairs = pairs[:a.limit]

if os.name == "nt":  # Windows에서 합성하는 동안 절전 막기 (프로그램이 끝나면 저절로 풀림)
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def load(m):
    person = np.array(Image.open(VT / "image" / m["person"]).convert("RGB"))
    cloth = np.array(Image.open(VT / "cloth" / m["cloth"]).convert("RGB"))
    cmask = (np.array(Image.open(VT / "cloth-mask" / m["cloth"]).convert("L")) > 127).astype(np.uint8)
    ag = (np.array(Image.open(VT / "agnostic-mask" / m["person"].replace(".jpg", "_mask.png")).convert("L")) > 127).astype(np.uint8)
    top = (np.array(Image.open(VT / "image-parse-v3" / m["person"].replace(".jpg", ".png"))) == UPPER).astype(np.uint8)
    wide = ag | cv2.dilate(top, np.ones((2 * DIL + 1, 2 * DIL + 1), np.uint8))
    k = json.loads((VT / "openpose_json" / m["person"].replace(".jpg", "_keypoints.json")).read_text())
    p = np.array(k["people"][0]["pose_keypoints_2d"], np.float32).reshape(-1, 3)
    return person, cloth, cmask, ag, wide, p


def shrink(im, size):
    """그림에 쓸 크기로 줄인 사진. 원래 크기 사진을 쌓아 두면 95쌍 x 가중치 3개에 약 1.8GB라, 줄인 것만 보관한다"""
    return np.array(Image.fromarray(im).resize(size))


def strength(img, box):
    """박스 선 세기 (테두리 안팎 밝기 차이의 가운데값), 비교할 바깥 테두리가 없으면 nan"""
    y1, y2, x1, x2 = box
    L = img.astype(np.float32) @ LUM
    H, W_ = L.shape
    v = []
    if y1 - 6 >= 0:
        v.append(np.abs(L[y1 + 2:y1 + 6, x1:x2].mean(0) - L[y1 - 6:y1 - 2, x1:x2].mean(0)))
    if y2 + 6 <= H:
        v.append(np.abs(L[y2 - 6:y2 - 2, x1:x2].mean(0) - L[y2 + 2:y2 + 6, x1:x2].mean(0)))
    if x1 - 6 >= 0:
        v.append(np.abs(L[y1:y2, x1 + 2:x1 + 6].mean(1) - L[y1:y2, x1 - 6:x1 - 2].mean(1)))
    if x2 + 6 <= W_:
        v.append(np.abs(L[y1:y2, x2 - 6:x2 - 2].mean(1) - L[y1:y2, x2 + 2:x2 + 6].mean(1)))
    return float(np.median(np.concatenate(v))) if v else float("nan")


def num(v, digits=2):
    return NA if np.isnan(v) else round(v, digits)


def out_path(n, m, name):
    return OUT / f"V{n:02d}_seed{m['seed']}_{name}.png"


# ---- 합성 ----
todo = {name: [(n, m) for n, m in pairs if not out_path(n, m, name).exists()] for name, _ in W}
fails = []
if any(todo.values()):
    from features.composition import AnyDoorComposer

    composer = AnyDoorComposer()  # 서버와 같은 설정, ANYDOOR_DIR 사용
    ns = composer._load()  # configs/inference.yaml의 공식 가중치로 불러옴
    from cldm.model import load_state_dict

    cur = {}
    ns["process_pairs"] = lambda ref_image, ref_mask, tar_image, tar_mask: inference_item(ref_image, ref_mask, tar_image, tar_mask, cur["p"])
    loaded = "original"
    for name, path in W:
        if not todo[name]:
            continue
        if path != loaded:
            sd = load_state_dict(str(OFFICIAL) if path == "original" else path, location="cpu")
            missing, unexpected = ns["model"].load_state_dict(sd, strict=False)
            print(f"{name}: 가중치 불러옴 {path} (빠진 키 {len(missing)}, 남는 키 {len(unexpected)})", flush=True)
            del sd
            gc.collect()
            loaded = path
        t0 = time.time()
        for k, (n, m) in enumerate(todo[name], 1):
            try:
                person, cloth, cmask, ag, wide, p = load(m)
                cur["p"] = p
                Image.fromarray(composer.compose(cloth, cmask, person, wide, seed=m["seed"])).save(out_path(n, m, name))
                print(f"{name} [{k}/{len(todo[name])}] V{n:02d} 저장 (누적 {(time.time() - t0) / 60:.0f}분)", flush=True)
            except Exception as e:  # 한 쌍이 실패해도 나머지는 계속
                fails.append(f"{name} V{n:02d} {type(e).__name__}: {e}")
                print(f"{name} [{k}/{len(todo[name])}] V{n:02d} 실패: {fails[-1]}", flush=True)

# ---- 포아송·숫자 ----
from features.composition import fix_seam  # noqa: E402  (앱 서버와 같은 박스 선 보정)

names = [name for name, _ in W]
rows, pics = [], {}
done = [(n, m) for n, m in pairs if all(out_path(n, m, name).exists() for name in names)]
for n, m in done:
    person, cloth, cmask, ag, wide, p = load(m)
    cb = server_crop(person, wide)
    H, W_ = person.shape[:2]
    box = (max(cb[0] + M, 0), min(cb[1] - M, H), max(cb[2] + M, 0), min(cb[3] - M, W_))  # 실제로 붙인 범위
    keep = np.zeros((H, W_), bool)
    keep[box[0]:box[1], box[2]:box[3]] = True
    keep &= cv2.dilate(wide, np.ones((2 * KEEP_DIL + 1, 2 * KEEP_DIL + 1), np.uint8)) == 0
    r = {"번호": f"V{n:02d}", "seed": m["seed"]}
    res, seam = {}, {}
    for name in names:
        res[name] = np.array(Image.open(out_path(n, m, name)).convert("RGB"))
        seam[name] = fix_seam(person, res[name], cb)
        r[f"박스 선 세기 {name} (포아송 전)"] = num(strength(res[name], box))
        r[f"박스 선 세기 {name} (포아송 후)"] = num(strength(seam[name], box))
        r[f"바뀌면 안 되는 곳 밝기 변화 {name}"] = (round(float((res[name][keep].astype(np.float32) @ LUM
                                                          - person[keep].astype(np.float32) @ LUM).mean()), 1) if keep.any() else NA)
    rows.append(r)
    view = person.copy()
    add = (wide > 0) & (ag == 0)
    view[ag > 0] = (view[ag > 0] * 0.45 + np.array([0, 90, 255]) * 0.55).astype(np.uint8)
    view[add] = (view[add] * 0.3 + np.array([255, 0, 0]) * 0.7).astype(np.uint8)
    # 그림에는 줄인 사진만 쓰므로 원래 크기 사진은 두지 않는다: 쌍별 그림용(TW x TH)과 모음 그림용(CW x CH)을 각각 원본에서 바로 줄여 보관
    pics[n] = ([shrink(im, (TW, TH)) for im in [person, cloth, view] + [res[x] for x in names] + [seam[x] for x in names if x != "original"]],
               [shrink(im, (CW, CH)) for im in [person, cloth] + [res[x] for x in names]])
if not rows:
    sys.exit(f"비교할 결과 없음 (실패 {len(fails)}건)")

with open(OUT / "compare_95.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)

lines = []
for name in names:
    s0 = [r[f"박스 선 세기 {name} (포아송 전)"] for r in rows if r[f"박스 선 세기 {name} (포아송 전)"] != NA]
    s1 = [r[f"박스 선 세기 {name} (포아송 후)"] for r in rows if r[f"박스 선 세기 {name} (포아송 후)"] != NA]
    dk = [r[f"바뀌면 안 되는 곳 밝기 변화 {name}"] for r in rows if r[f"바뀌면 안 되는 곳 밝기 변화 {name}"] != NA]
    lines.append(f"{name} ({len(s0)}장): 박스 선 세기 평균 {np.mean(s0):.2f} → 포아송 후 {np.mean(s1):.2f}, "
                 f"바뀌면 안 되는 곳 밝기 변화 평균 {np.mean(dk):+.1f}" if s0 and s1 and dk else f"{name}: 측정 불가")
for t in lines:
    print(t, flush=True)

# ---- 그림 ----
F, FS, FB, FT = font(15), font(17), font(19), font(24)
HEADS = ["원래 사진", "입힐 옷", "다시 그리는 영역"] + names + [f"{x} + 포아송" for x in names if x != "original"]
LEGEND = ["같은 새 입력·같은 seed로 그림 → 결과 차이는 가중치 때문, original = AnyDoor 공식 가중치 (재학습 전, 새 입력을 배운 적 없음)",
          "다시 그리는 영역: 파랑 = 상체 + 팔, 빨강 = 더한 원래 상의",
          "포아송 = 앱 서버의 박스 선 보정 (fix_seam), 원본 복원은 안 붙임 / 박스 선 세기 = 다시 그린 정사각형 테두리 안팎 밝기 차이 (0 = 선 없음)",
          "확인할 것: 남는 자리 맨살, 원래 옷 조각 없음, 옷 색이 입힐 옷과 같은지, 없던 물건 (벨트·얼룩·레이스 층), 바지 색"]


def text_w(fnt, s):
    try:
        return fnt.getlength(s)
    except AttributeError:  # 한글 글꼴이 없어 기본 글꼴을 쓸 때
        return len(s) * 8


def wrap(text, fnt, width):
    """글자 폭을 재서 width를 넘으면 줄을 바꾼다 (띄어쓰기 단위)"""
    out, cur = [], ""
    for word in text.split(" "):
        test = f"{cur} {word}" if cur else word
        if text_w(fnt, test) <= width or not cur:
            cur = test
        else:
            out.append(cur)
            cur = word
    return out + [cur]


def legend_lines(fnt, width):
    return [ln for t in LEGEND for ln in wrap("• " + t, fnt, width)]


row_of = {r["번호"]: r for r in rows}


def tile(n, m, with_legend=True):
    ims = pics[n][0]  # 이미 (TW, TH)로 줄여 둔 사진
    width = len(ims) * (TW + GAP)
    leg = legend_lines(F, width - 8) if with_legend else []
    t = Image.new("RGB", (width, TH + 64 + 24 * len(leg)), "white")
    d = ImageDraw.Draw(t)
    r = row_of[f"V{n:02d}"]
    d.text((4, 2), f"V{n:02d} (seed {m['seed']})   박스 선 세기 " + " / ".join(
        f"{x} {r[f'박스 선 세기 {x} (포아송 전)']}→{r[f'박스 선 세기 {x} (포아송 후)']}" for x in names), fill="black", font=FB)
    for j, (h, im) in enumerate(zip(HEADS, ims)):
        d.text((j * (TW + GAP) + 2, 30), h, fill="black", font=F)
        t.paste(Image.fromarray(im), (j * (TW + GAP), 52))
    y = TH + 60
    for ln in leg:
        d.text((4, y), ln, fill=(60, 60, 60), font=F)
        y += 24
    return t


for n, m in done:
    tile(n, m).save(OUT / "compare" / f"V{n:02d}.jpg", quality=90)

# 모음 그림: 12쌍씩, 한 칸 = 원래 사진 | 입힐 옷 | 가중치별 결과 (포아송 전)
CELL = (2 + len(names)) * (CW + 2) + 24
for page in range(0, len(done), PER):
    chunk = done[page:page + PER]
    nrow = (len(chunk) + COLS - 1) // COLS
    leg = legend_lines(F, COLS * CELL - 16)
    sheet = Image.new("RGB", (COLS * CELL, 84 + nrow * (CH + 30) + 24 * len(leg) + 16), "white")
    d = ImageDraw.Draw(sheet)
    d.text((4, 4), f"재학습 가중치 비교 95장 ({page + 1}~{page + len(chunk)})", fill="black", font=FT)
    d.text((4, 38), "칸마다: 원래 사진 | 입힐 옷 | " + " | ".join(names) + " (포아송 전)", fill="black", font=FS)
    for k, (n, m) in enumerate(chunk):
        x, y = (k % COLS) * CELL, 70 + (k // COLS) * (CH + 30)
        d.text((x + 2, y), f"V{n:02d}", fill="black", font=FB)
        for j, im in enumerate(pics[n][1]):  # 이미 (CW, CH)로 줄여 둔 사진
            sheet.paste(Image.fromarray(im), (x + j * (CW + 2), y + 26))
    y = 76 + nrow * (CH + 30)
    for ln in leg:
        d.text((4, y), ln, fill=(60, 60, 60), font=F)
        y += 24
    sheet.save(OUT / f"overview_{page // PER + 1}.jpg", quality=88)

# 고른 사진만 모음 (--pick)
picks = [p_.strip().upper() for p_ in a.pick.split(",") if p_.strip()]
chosen = [(n, m) for n, m in done if f"V{n:02d}" in picks]
if chosen:
    tiles = [tile(n, m, with_legend=False) for n, m in chosen]
    width = tiles[0].width
    leg = legend_lines(F, width - 16) + [f"• 숫자 ({len(rows)}장): " + t for t in lines]
    sheet = Image.new("RGB", (width, 50 + sum(x.height + 10 for x in tiles) + 24 * len(leg) + 16), "white")
    d = ImageDraw.Draw(sheet)
    d.text((4, 6), "재학습 가중치 비교: 고른 사진", fill="black", font=FT)
    y = 50
    for x in tiles:
        sheet.paste(x, (0, y))
        y += x.height + 10
    for ln in leg:
        d.text((4, y), ln, fill=(60, 60, 60), font=F)
        y += 24
    sheet.save(OUT / "compare_pick.jpg", quality=90)

print(f"완료: 비교 {len(done)}쌍, 실패 {len(fails)}건", flush=True)
for f_ in fails:
    print("  " + f_, flush=True)
print("저장", OUT, flush=True)
