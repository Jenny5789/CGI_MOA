"""쉐이프리스 변환본(Shapeless_AnyDoor)에 팀 재학습(scripts/retrain, 브랜치 cej-retrain)이 요구하는 입력을 더해 VITON-HD 폴더 형식으로 만듦

팀 학습 재료(retrain_dataset.py)가 VITON-HD 에서 읽는 것: image, cloth, cloth-mask, image-parse-v3(5=상의), agnostic-mask, openpose_json
쉐이프리스에 없는 두 가지를 라벨에서 만듦
  - openpose_json : COCO 17점 → OpenPose BODY_25 (목 = 양 어깨 가운데, 골반 가운데 = 양 골반 가운데, 나머지는 같은 관절)
  - agnostic-mask : agnostic_pose.py 의 관절 점 영역 - 머리 - 하체, 착용 상의는 반드시 포함
                    VITON-HD 학습용 300장에서 같은 규칙의 IoU 중앙값 0.967 (제공 마스크 재현 확인)
                    옷 모양이 아니라 자세를 따르므로, 옷이 안 덮는 배·팔·허리도 다시 그릴 영역에 들어감 (VITON-HD 와 같은 성질)
머리·하체 폴리곤: 폴리곤 수 = 키 수면 키로 바로 찾음 (1 얼굴, 4·5 다리, 7 기본 하의, 19 팬츠, 20 스커트).
  한 클래스가 여러 조각이라 순서 대응이 깨진 경우(약 15%)에는 얼굴 = 코·눈·귀 점이 든 폴리곤,
  하체 = 옷·얼굴이 아니고 팔꿈치·손목 점이 없으면서 무릎·발목 점이 있거나 가운데가 골반보다 아래인 폴리곤
쉐이프리스 '얼굴'은 머리카락까지 포함해서 머리카락도 다시 그릴 영역에서 빠짐 (VITON-HD 는 머리카락 일부가 들어감)

기존 파일은 건드리지 않고 <out>/train 에 하드링크로 연결. 상의류만 변환 (팀 방식은 상의 문제 개선용)

python scripts/shapeless_to_viton.py --limit 50
python scripts/shapeless_to_viton.py --force     # 만들어 둔 agnostic-mask, openpose_json 을 다시 만듦
"""
import argparse
import json
import os
import shutil
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preprocess_shapeless as P  # noqa: E402
from agnostic_pose import agnostic  # noqa: E402

SRC_OUT = Path(r"C:\CGI_MOA\Dataset\Shapeless_AnyDoor\Training")
DST = Path(r"C:\CGI_MOA\Dataset\Shapeless_Viton")
LABEL_SRC = P.DEFAULT_SRC / "Training"
UPPER = {"가디건", "블라우스", "셔츠", "스웨터", "재킷", "점퍼", "코트", "탑", "티셔츠", "패딩", "베스트"}
LINK_DIRS = {"cloth": ".jpg", "cloth-mask": ".jpg", "image": ".jpg", "image-parse-v3": ".png"}
HEAD_KEYS, LOWER_KEYS = {"1"}, {"4", "5", "7", "19", "20"}
# COCO 17 점 → BODY_25 번호
COCO_TO_B25 = {0: 0, 6: 2, 8: 3, 10: 4, 5: 5, 7: 6, 9: 7, 12: 9, 14: 10, 16: 11, 11: 12, 13: 13, 15: 14}
C_ARM = (7, 8, 9, 10)  # 팔꿈치·손목
C_HIP, C_KNEE_ANKLE = (11, 12), (13, 14, 15, 16)


def inside(poly, pt):
    c = np.array(poly, np.float32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(c, (float(pt[0]), float(pt[1])), False) >= 0


def part_polygons(label, cls, kp):
    """(옷, 머리, 하체) 폴리곤 목록, 원본 좌표"""
    a = label["annotation"][0]
    seg = a["segmentation"]
    keys, vals = list(seg.keys()), list(seg.values())
    cloth = P.worn_cloth_polygons(label, cls)
    positional = len(keys) > 1 and all(v == vals[0] for v in vals)
    if positional and len(vals[0]) == len(keys):
        return cloth, [p for k, p in zip(keys, vals[0]) if k in HEAD_KEYS], [p for k, p in zip(keys, vals[0]) if k in LOWER_KEYS]
    if not positional:  # 키마다 폴리곤이 따로 있는 일반 형식
        return cloth, [p for k in keys if k in HEAD_KEYS for p in seg[k]], [p for k in keys if k in LOWER_KEYS for p in seg[k]]
    polys = vals[0]
    fi = P.face_poly_index(polys, a["keypoint"])
    head = [polys[fi]] if fi is not None else []
    hip_y = np.mean([kp[i][1] for i in C_HIP if kp[i][2] > 0]) if any(kp[i][2] > 0 for i in C_HIP) else None
    lower = []
    for j, p in enumerate(polys):
        if j < len(cloth) or j == fi:
            continue
        if any(kp[i][2] > 0 and inside(p, kp[i]) for i in C_ARM):
            continue
        low_pt = any(kp[i][2] > 0 and inside(p, kp[i]) for i in C_KNEE_ANKLE)
        below = hip_y is not None and np.array(p).reshape(-1, 2)[:, 1].mean() > hip_y
        if low_pt or below:
            lower.append(p)
    return cloth, head, lower


def body25(kp, box):
    x0, y0, cw, ch = box
    sx, sy = P.OUT_W / cw, P.OUT_H / ch
    b = np.zeros((25, 3))
    for c, o in COCO_TO_B25.items():
        x, y, v = kp[c]
        if v > 0:
            b[o] = ((x - x0) * sx, (y - y0) * sy, 1.0)
    if b[2, 2] and b[5, 2]:
        b[1] = ((b[2, 0] + b[5, 0]) / 2, (b[2, 1] + b[5, 1]) / 2, 1.0)  # 목
    if b[9, 2] and b[12, 2]:
        b[8] = ((b[9, 0] + b[12, 0]) / 2, (b[9, 1] + b[12, 1]) / 2, 1.0)  # 골반 가운데
    return b


def convert(task):
    row, dst, force = task
    i, cat, cls = row["id"], row["cat"], row["cls"]
    dst = Path(dst)
    outs = {d: dst / d / f"{i}{e}" for d, e in LINK_DIRS.items()}
    outs["agnostic-mask"] = dst / "agnostic-mask" / f"{i}_mask.png"
    outs["openpose_json"] = dst / "openpose_json" / f"{i}_keypoints.json"
    if not force and all(p.exists() for p in outs.values()):
        return i, "ok"
    try:
        label = P.read_label(P.label_zip_path(LABEL_SRC, "제품 착용", cat, "TL"), i)
        info = label["info"][0]["image"]
        w, h = int(info["width"]), int(info["height"])
        box = P.crop_box(P.all_polygons(label), w, h, 0.12)
        kp = np.array(label["annotation"][0]["keypoint"], np.float64).reshape(-1, 3)
        cloth, head, lower = part_polygons(label, cls, kp)
        b25 = body25(kp, box)
        if not (b25[2, 2] and b25[5, 2]):
            return i, "no_shoulders"
        cm = P.polys_to_mask(cloth, box).astype(bool)
        keep_out = (P.polys_to_mask(head, box) | P.polys_to_mask(lower, box)).astype(bool) & ~cm
        ag = agnostic(b25, P.OUT_H, P.OUT_W, keep_out, cm)
        if ag.sum() < 1000:
            return i, "agnostic_small"
        # 같은 파일에 덮어쓰기(하드링크로 연결된 Retrain_Mix 쪽도 같이 바뀜)
        Image.fromarray(ag.astype(np.uint8) * 255).save(outs["agnostic-mask"])
        with open(outs["openpose_json"], "w") as f:
            json.dump({"version": 1.3, "people": [{"pose_keypoints_2d": b25.reshape(-1).round(2).tolist()}]}, f)
        for d, e in LINK_DIRS.items():
            if not outs[d].exists():
                try:
                    os.link(SRC_OUT / d / f"{i}{e}", outs[d])
                except OSError:
                    shutil.copyfile(SRC_OUT / d / f"{i}{e}", outs[d])
        return i, "ok"
    except KeyError as e:
        return i, str(e).strip("'")
    except ValueError as e:
        return i, str(e)
    except Exception:
        return i, "error"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DST)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="agnostic-mask, openpose_json 을 다시 만듦")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    dst = a.out / "train"
    for d in list(LINK_DIRS) + ["agnostic-mask", "openpose_json"]:
        (dst / d).mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in open(SRC_OUT / "pairs.jsonl", encoding="utf-8")]
    rows = [r for r in rows if r["cat"] in UPPER]
    if a.limit:
        rows = rows[: a.limit]
    print(f"상의류 {len(rows)}쌍 변환")
    skipped, ok_ids = Counter(), set()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, st in tqdm(ex.map(convert, [(r, str(dst), a.force) for r in rows], chunksize=32), total=len(rows)):
            if st == "ok":
                ok_ids.add(i)
            else:
                skipped[st] += 1
    with open(dst / "meta.jsonl", "w", encoding="utf-8") as f:
        for r in sorted((r for r in rows if r["id"] in ok_ids), key=lambda r: r["id"]):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"변환": len(ok_ids), "건너뜀": dict(skipped)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
