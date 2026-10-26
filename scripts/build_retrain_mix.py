"""팀 재학습(브랜치 cej-retrain 의 scripts/retrain)용으로 VITON-HD 와 쉐이프리스(상의류)를 한 폴더로 합치고 학습 쌍 목록을 만듦

합친 폴더: <out>/train  (VITON-HD 학습용 + shapeless_to_viton.py 결과를 하드링크로 연결, 용량 거의 없음)
  → 서버에서 VITON_TRAIN_DIR=<out>/train 으로 두면 팀 스크립트가 그대로 읽음
목록(<out>/ids_*.txt, 한 줄 = 사진 번호, 그룹, 옷 아랫단 위치): 팀 retrain_train.py 가 읽는 ids.txt 형식
  ids_viton.txt            VITON-HD 만 (팀 기존 방식)
  ids_shapeless_front.txt  쉐이프리스 정면만
  ids_shapeless_all.txt    쉐이프리스 모든 각도 (참고용)
  ids_mix_front.txt        VITON-HD + 쉐이프리스 정면
쓰려는 목록을 학습 결과 폴더에 ids.txt 로 복사하면 됨
거르기는 팀 retrain_dataset.usable (부위 지도·옷 마스크·관절 점) 그대로. 각도는 거르지 않아서 여기서 따로 나눔

python scripts/build_retrain_mix.py --retrain-dir <팀 scripts/retrain 폴더>
"""
import argparse
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

VITON = Path(r"C:\CGI_MOA\Dataset\TryOn\VitonHD\train")
SHP = Path(r"C:\CGI_MOA\Dataset\Shapeless_Viton\train")
OUT = Path(r"C:\CGI_MOA\Dataset\Retrain_Mix")
SUBS = {"image": ".jpg", "cloth": ".jpg", "cloth-mask": ".jpg", "image-parse-v3": ".png",
        "agnostic-mask": "_mask.png", "openpose_json": "_keypoints.json"}


def link_all(src_root, dst_root, ids):
    n = 0
    for i in ids:
        for d, e in SUBS.items():
            s, t = src_root / d / f"{i}{e}", dst_root / d / f"{i}{e}"
            if t.exists():
                continue
            try:
                os.link(s, t)
            except OSError:
                shutil.copyfile(s, t)
            n += 1
    return n


def check(i):
    import retrain_dataset as R  # VITON_TRAIN_DIR 환경 변수는 main 에서 먼저 지정
    return i, R.usable(i)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retrain-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    dst = a.out / "train"
    for d in SUBS:
        (dst / d).mkdir(parents=True, exist_ok=True)

    viton_ids = sorted(p.stem for p in (VITON / "image").glob("*.jpg"))
    meta = {}
    for line in open(SHP / "meta.jsonl", encoding="utf-8"):
        r = json.loads(line)
        meta[r["id"]] = r
    shp_ids = sorted(meta)
    print(f"VITON-HD {len(viton_ids)}쌍, 쉐이프리스 상의류 {len(shp_ids)}쌍 연결")
    link_all(VITON, dst, viton_ids)
    link_all(SHP, dst, shp_ids)

    os.environ["ANYDOOR_DIR"] = os.environ.get("ANYDOOR_DIR", r"C:\CGI_MOA\checkpoints\AnyDoor")
    os.environ["VITON_TRAIN_DIR"] = str(dst)
    sys.path.insert(0, str(a.retrain_dir))
    ids = viton_ids + shp_ids
    with ProcessPoolExecutor(a.workers) as ex:
        res = dict(tqdm(ex.map(check, ids, chunksize=32), total=len(ids)))
    ok = {i: b for i, (good, b) in res.items() if good}

    def lines(group, sel):
        return [f"{i}\t{group}\t{ok[i]:.2f}" for i in sel if i in ok]

    v = lines("viton", viton_ids)
    sf = lines("shapeless", [i for i in shp_ids if meta[i]["angle"] == "정면"])
    sa = lines("shapeless", shp_ids)
    for name, ls in (("viton", v), ("shapeless_front", sf), ("shapeless_all", sa), ("mix_front", v + sf)):
        (a.out / f"ids_{name}.txt").write_text("\n".join(ls), encoding="utf-8")

    st = defaultdict(lambda: [0, 0])  # 항목 → [전체, 통과]
    for i in shp_ids:
        for k in ("angle", "cat"):
            st[(k, meta[i][k])][0] += 1
            st[(k, meta[i][k])][1] += i in ok
    report = {"viton": {"전체": len(viton_ids), "통과": len(v)},
              "shapeless": {"전체": len(shp_ids), "통과": len(sa)},
              "shapeless_정면": {"전체": sum(meta[i]["angle"] == "정면" for i in shp_ids), "통과": len(sf)},
              "쉐이프리스 항목별 [전체, 통과]": {f"{k}:{n}": v2 for (k, n), v2 in sorted(st.items())},
              "쉐이프리스 정면 포즈별 통과": dict(Counter(meta[i]["pose"] for i in ok if i in meta and meta[i]["angle"] == "정면"))}
    (a.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
