"""쉐이프리스 의류 및 포즈 데이터를 AnyDoor 학습용(VITON-HD 폴더 형식)으로 변환

입력: AI Hub 원본 폴더 (01.원천데이터 zip 그대로 또는 풀어 둔 jpg + 02.라벨링데이터 zip 그대로).
  원천 zip 에서 이미지를 바로 읽으므로 원본 jpg 를 디스크에 풀 필요가 없음
출력: <out>/cloth, cloth-mask, image, image-parse-v3, pairs.jsonl, report.json
  - cloth            제품(옷) 사진 768x1024
  - cloth-mask       제품 마스크 (jpg, 0/255)
  - image            그 옷을 입은 모델 사진 768x1024
  - image-parse-v3   착용 사진의 옷 영역 (png, 옷=5, 나머지 0)
AnyDoor datasets/vitonhd.py 가 그대로 읽는 구조라, configs/datasets.yaml 의 VitonHD.image_dir 만 바꾸면 학습 가능

라벨 JSON 특이점: segmentation 의 모든 클래스 키가 같은 폴리곤 목록을 반복하고,
키 순서와 폴리곤 순서가 1:1 로 대응함 (예: 키 [16,1,2,...] ↔ 폴리곤 [티셔츠, 얼굴, 왼팔, ...])

실행 예:
  python scripts/preprocess_shapeless.py --limit 200      # 먼저 200쌍만 시험
  python scripts/preprocess_shapeless.py                  # 전체 (이미 만든 파일은 건너뜀, 압축 해제 중이면 나중에 다시 실행)
"""
import argparse
import json
import os
import shutil
import sys
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

DEFAULT_SRC = Path(r"C:\Users\AISW_203_101\Downloads\011.쉐이프리스 의류 및 포즈 데이터\01-1.정식개방데이터")
DEFAULT_OUT = Path(r"C:\CGI_MOA\Dataset\Shapeless_AnyDoor")
OUT_W, OUT_H = 768, 1024  # VITON-HD 와 같은 3:4. 원본(3024x4032, 3072x4096)도 3:4
PARSE_CLOTH = 5  # vitonhd.py 가 tar_mask == 5 로 옷 영역을 읽음
JPEG_Q = 95

_zip_cache = {}  # 프로세스마다 zip 핸들과 파일 목록을 한 번만 열어 재사용


def read_img(buf):
    # cv2.imread 는 한글 경로를 못 읽어서 바이트로 읽어 imdecode 사용
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("decode")
    return img


def write_jpg(path, img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    tmp = str(path) + ".tmp"
    buf.tofile(tmp)
    os.replace(tmp, path)


def write_png(path, img):
    tmp = str(path) + ".tmp"
    img.save(tmp, format="PNG")
    os.replace(tmp, path)


def read_label(base, stem):
    """라벨 JSON 읽기. <base>.zip 이 있으면 zip 에서, 없으면 풀어 둔 <base>/ 폴더에서"""
    zp = base + ".zip"
    if os.path.exists(zp):
        z = _zip_cache.get(zp)
        if z is None:
            zf = zipfile.ZipFile(zp)
            z = _zip_cache[zp] = (zf, set(zf.namelist()))
        zf, names = z
        name = f"/{stem}.json"
        if name not in names:
            raise KeyError("no_label")
        return json.loads(zf.read(name))
    path = os.path.join(base, f"{stem}.json")
    if not os.path.exists(path):
        raise KeyError("no_label")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def class_polygons(label):
    """라벨 JSON 에서 {클래스 키: [폴리곤...]} 을 꺼냄"""
    seg = label["annotation"][0]["segmentation"]
    keys, vals = list(seg.keys()), list(seg.values())
    if len(keys) > 1 and all(v == vals[0] for v in vals):
        polys = vals[0]
        if len(polys) != len(keys):
            raise ValueError("poly_count")
        return {k: [p] for k, p in zip(keys, polys)}  # 키 순서 ↔ 폴리곤 순서
    return {k: v for k, v in seg.items()}


def face_poly_index(polys, keypoint):
    """코·눈·귀 키포인트가 가장 많이 들어 있는 폴리곤 번호 (0번은 옷이라 제외)"""
    pts = [(keypoint[i * 3], keypoint[i * 3 + 1]) for i in range(5) if keypoint[i * 3 + 2] > 0 and keypoint[i * 3] > 0]
    best, found = 0, None
    for j, p in enumerate(polys):
        if j == 0:
            continue
        contour = np.array(p, np.float32).reshape(-1, 1, 2)
        n = sum(cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0 for x, y in pts)
        if n > best:
            best, found = n, j
    return found


def worn_cloth_polygons(label, cls):
    """착용 사진 JSON 에서 옷 폴리곤만 꺼냄.
    폴리곤 수 = 키 수면 순서 대응. 더 많으면 한 클래스가 여러 조각이라 대응이 깨지는데(전체의 약 15%),
    옷 클래스는 항상 첫 키이고 둘째 키는 얼굴(1)이라서, 얼굴 앞쪽 폴리곤이 전부 옷 조각임"""
    a = label["annotation"][0]
    seg = a["segmentation"]
    keys, vals = list(seg.keys()), list(seg.values())
    if keys[0] != cls:
        raise ValueError("class_not_first")
    if len(keys) == 1:
        return vals[0]
    if not all(v == vals[0] for v in vals):
        return seg[cls]
    polys = vals[0]
    if len(polys) == len(keys):
        return polys[:1]
    if keys[1] != "1":
        raise ValueError("poly_count")
    fi = face_poly_index(polys, a["keypoint"])
    if fi is None:
        raise ValueError("face_not_found")
    return polys[:fi]


def all_polygons(label):
    seg = label["annotation"][0]["segmentation"]
    vals = list(seg.values())
    if len(vals) > 1 and all(v == vals[0] for v in vals):
        return vals[0]
    return [p for v in vals for p in v]


def crop_box(polys, w, h, margin):
    """폴리곤 전체를 감싸는 3:4 크롭 박스 (x0, y0, cw, ch). 이미지 밖으로 나가면 안쪽으로 밀어 넣음"""
    pts = np.concatenate([np.array(p, np.float64).reshape(-1, 2) for p in polys])
    x1, y1 = pts.min(0)
    x2, y2 = pts.max(0)
    ch = max((y2 - y1), (x2 - x1) * OUT_H / OUT_W) * (1 + 2 * margin)
    ch = min(ch, h, w * OUT_H / OUT_W)
    cw = ch * OUT_W / OUT_H
    x0 = min(max((x1 + x2) / 2 - cw / 2, 0), w - cw)
    y0 = min(max((y1 + y2) / 2 - ch / 2, 0), h - ch)
    return int(round(x0)), int(round(y0)), int(round(cw)), int(round(ch))


def polys_to_mask(polys, box):
    x0, y0, cw, ch = box
    mask = np.zeros((OUT_H, OUT_W), np.uint8)
    sx, sy = OUT_W / cw, OUT_H / ch
    for p in polys:
        pts = ((np.array(p, dtype=np.float64).reshape(-1, 2) - [x0, y0]) * [sx, sy]).round().astype(np.int32)
        if len(pts) >= 3:
            cv2.fillPoly(mask, [pts], 1)
    return mask


def load_cropped(buf, label, margin):
    """원본을 읽고 JSON 크기와 맞는지 확인한 뒤, 사람/옷 영역을 3:4 로 잘라 768x1024 로 줄임. (이미지, 크롭 박스) 반환"""
    info = label["info"][0]["image"]
    jw, jh = int(info["width"]), int(info["height"])
    img = read_img(buf)
    h, w = img.shape[:2]
    if (w, h) != (jw, jh):
        raise ValueError("size_mismatch")
    if abs(w / h - OUT_W / OUT_H) > 0.02:
        raise ValueError("aspect")
    box = (0, 0, w, h) if margin is None else crop_box(all_polygons(label), w, h, margin)
    x0, y0, cw, ch = box
    return cv2.resize(img[y0:y0 + ch, x0:x0 + cw], (OUT_W, OUT_H), interpolation=cv2.INTER_AREA), box


def split_pair_path(p):
    # "/원천데이터/제품 착용/가디건/KSOT0400M332P11A1.jpg" -> ("제품 착용", "가디건", "KSOT0400M332P11A1")
    parts = p.strip("/").split("/")
    return parts[1], parts[2], Path(parts[3]).stem


_img_zip_cache = {}


def fetch_image_bytes(src, kind, cat, stem, split_prefix):
    """원천 이미지를 압축 파일(01.원천데이터/TS_..*.zip)에서 바로 읽음. zip 이 없으면 풀어 둔 폴더에서 읽음.
    zip 에서 읽으면 원본 jpg 를 디스크에 풀 필요가 없음. 못 찾으면 None"""
    key = (str(src), kind, cat)
    zips = _img_zip_cache.get(key)
    if zips is None:
        zips = []
        for zp in sorted((src / "01.원천데이터").glob(f"{split_prefix}_{kind}_{cat}*.zip")):
            zf = zipfile.ZipFile(zp)
            zips.append((zf, set(zf.namelist())))
        _img_zip_cache[key] = zips
    name = f"/{stem}.jpg"
    for zf, names in zips:
        if name in names:
            return np.frombuffer(zf.read(name), dtype=np.uint8)
    path = src / "01.원천데이터" / f"{split_prefix}_{kind}_{cat}" / f"{stem}.jpg"
    if path.exists():
        return np.fromfile(str(path), dtype=np.uint8)
    for d in (src / "01.원천데이터").glob(f"{split_prefix}_{kind}_{cat}_*"):  # 분할 폴더(_1 등)
        if d.is_dir() and (d / f"{stem}.jpg").exists():
            return np.fromfile(str(d / f"{stem}.jpg"), dtype=np.uint8)
    return None


def label_zip_path(src, kind, cat, label_prefix):
    return str(src / "02.라벨링데이터" / f"{label_prefix}_{kind}_{cat}")  # 뒤에 .zip 이 붙은 파일 또는 같은 이름 폴더


def ratio_ok(mask, lo, hi):
    r = float(mask.mean())
    return lo <= r <= hi, r


def do_product(task):
    """제품 사진 1장: 줄이기 + 옷 마스크 → _product 캐시"""
    kind, cat, stem, src, out, lp, sp, lo, hi, margin = task
    od = Path(out) / "_product"
    if (od / f"{stem}.jpg").exists() and (od / f"{stem}_mask.jpg").exists():
        return stem, "ok", None
    try:
        buf = fetch_image_bytes(Path(src), kind, cat, stem, sp)
        if buf is None:
            return stem, "missing_image", None
        label = read_label(label_zip_path(Path(src), kind, cat, lp), stem)
        polys_by_cls = class_polygons(label)
        if len(polys_by_cls) != 1:
            return stem, "product_multi_class", None
        img, box = load_cropped(buf, label, margin)
        mask = polys_to_mask(next(iter(polys_by_cls.values())), box)
        ok, r = ratio_ok(mask, lo, hi)
        if not ok:
            return stem, "mask_ratio", r
        write_jpg(od / f"{stem}.jpg", img)
        write_jpg(od / f"{stem}_mask.jpg", mask * 255)
        cls = next(iter(polys_by_cls.keys()))
        (od / f"{stem}.cls").write_text(f"{cls},{r:.4f}")
        return stem, "ok", r
    except KeyError as e:
        return stem, str(e).strip("'"), None
    except ValueError as e:
        return stem, str(e), None
    except Exception:
        return stem, "error", None


def link_or_copy(src, dst, use_link):
    if dst.exists():
        return
    if use_link:
        try:
            os.link(src, dst)
            return
        except OSError:
            pass
    shutil.copyfile(src, dst)


def do_pair(task):
    """착용 사진 1장: 줄이기 + 옷 영역 마스크, 제품 캐시는 링크로 연결"""
    pair, src, out, lp, sp, lo, hi, use_link, margin = task
    out = Path(out)
    f_kind, f_cat, f_stem = split_pair_path(pair["from"])
    r_kind, r_cat, r_stem = split_pair_path(pair["result"])
    pdir = out / "_product"
    paths = {
        "cloth": out / "cloth" / f"{r_stem}.jpg",
        "cloth-mask": out / "cloth-mask" / f"{r_stem}.jpg",
        "image": out / "image" / f"{r_stem}.jpg",
        "image-parse-v3": out / "image-parse-v3" / f"{r_stem}.png",
    }
    try:
        cls_file = pdir / f"{f_stem}.cls"
        if not cls_file.exists():
            return r_stem, "product_unavailable", None
        prod_cls, prod_ratio = cls_file.read_text().split(",")
        done = all(p.exists() for p in paths.values())
        meta_path = out / "_meta" / f"{r_stem}.json"
        if done and meta_path.exists():
            return r_stem, "ok", json.loads(meta_path.read_text(encoding="utf-8"))
        buf = fetch_image_bytes(Path(src), r_kind, r_cat, r_stem, sp)
        if buf is None:
            return r_stem, "missing_image", None
        label = read_label(label_zip_path(Path(src), r_kind, r_cat, lp), r_stem)
        cloth_polys = worn_cloth_polygons(label, prod_cls)
        img, box = load_cropped(buf, label, margin)
        mask = polys_to_mask(cloth_polys, box)
        ok, r = ratio_ok(mask, lo, hi)
        if not ok:
            return r_stem, "mask_ratio", r
        write_jpg(paths["image"], img)
        parse = Image.fromarray(mask * PARSE_CLOTH, mode="L").convert("P")
        write_png(paths["image-parse-v3"], parse)
        link_or_copy(pdir / f"{f_stem}.jpg", paths["cloth"], use_link)
        link_or_copy(pdir / f"{f_stem}_mask.jpg", paths["cloth-mask"], use_link)
        info = label["info"][0]
        meta = dict(cat=r_cat, product=f_stem, cls=prod_cls, product_ratio=float(prod_ratio), worn_ratio=round(r, 4),
                    model_id=info.get("model_id"), pose=info["image"].get("pose") or info.get("pose"),
                    angle=info["image"].get("angle"))
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return r_stem, "ok", meta
    except KeyError as e:
        return r_stem, str(e).strip("'"), None
    except ValueError as e:
        return r_stem, str(e), None
    except Exception:
        return r_stem, "error", None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="01-1.정식개방데이터 폴더")
    ap.add_argument("--split", default="Training", choices=["Training", "Validation"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="출력 폴더 (아래에 split 이름 폴더가 생김)")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N쌍만 처리 (시험용)")
    ap.add_argument("--cats", nargs="+", help="이 종류만 처리 (예: 셔츠 팬츠). 디스크가 모자라면 종류별로 나눠 실행")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--min-ratio", type=float, default=0.01, help="옷 영역 비율 하한 (AnyDoor check_mask_area 와 같음)")
    ap.add_argument("--max-ratio", type=float, default=0.64, help="옷 영역 비율 상한")
    ap.add_argument("--crop-margin", type=float, default=0.12,
                    help="사람(제품은 옷) 영역을 3:4 로 자를 때 사방 여백 비율. -1 이면 자르지 않고 전체를 줄임")
    ap.add_argument("--no-hardlink", action="store_true", help="제품 사진을 하드링크 대신 복사")
    a = ap.parse_args()

    margin = None if a.crop_margin < 0 else a.crop_margin
    sp, lp = ("TS", "TL") if a.split == "Training" else ("VS", "VL")
    src = a.src / a.split
    out = a.out / a.split
    for d in ("_product", "_meta", "cloth", "cloth-mask", "image", "image-parse-v3"):
        (out / d).mkdir(parents=True, exist_ok=True)

    pair_base = str(src / "02.라벨링데이터" / f"{lp}_페어")
    if os.path.exists(pair_base + ".zip"):
        with zipfile.ZipFile(pair_base + ".zip") as z:
            pairs = json.loads(z.read(z.namelist()[0]))
    else:
        with open(os.path.join(pair_base, "Pair.json"), encoding="utf-8") as f:
            pairs = json.load(f)
    seen, uniq = set(), []
    for p in pairs:  # result 기준 중복 제거
        if p["result"] not in seen:
            seen.add(p["result"])
            uniq.append(p)
    if a.cats:
        uniq = [p for p in uniq if split_pair_path(p["result"])[1] in a.cats]
    pairs = uniq[: a.limit] if a.limit else uniq
    print(f"쌍 {len(pairs)}개 (Pair.json 중복 제거 후 {len(uniq)})  작업자 {a.workers}명")

    skipped = Counter()
    products = {}
    for p in pairs:
        k, c, s = split_pair_path(p["from"])
        products[s] = (k, c)

    with ProcessPoolExecutor(a.workers) as ex:
        tasks = [(k, c, s, str(src), str(out), lp, sp, a.min_ratio, a.max_ratio, margin) for s, (k, c) in products.items()]
        print(f"[1/2] 제품 사진 {len(tasks)}장")
        for stem, status, _ in tqdm(ex.map(do_product, tasks, chunksize=16), total=len(tasks)):
            if status != "ok":
                skipped[f"product:{status}"] += 1

        tasks = [(p, str(src), str(out), lp, sp, a.min_ratio, a.max_ratio, not a.no_hardlink, margin) for p in pairs]
        print(f"[2/2] 착용 사진 {len(tasks)}장")
        n_ok = 0
        with open(out / "pairs.jsonl", "w", encoding="utf-8") as fo:
            for stem, status, meta in tqdm(ex.map(do_pair, tasks, chunksize=16), total=len(tasks)):
                if status == "ok":
                    n_ok += 1
                    fo.write(json.dumps({"id": stem, **meta}, ensure_ascii=False) + "\n")
                else:
                    skipped[f"pair:{status}"] += 1

    report = {"split": a.split, "pairs_total": len(pairs), "pairs_ok": n_ok, "skipped": dict(skipped),
              "size": [OUT_W, OUT_H], "crop_margin": margin, "ratio_range": [a.min_ratio, a.max_ratio]}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if skipped.get("pair:missing_image") or skipped.get("product:missing_image"):
        print("원천 이미지가 아직 없는 쌍이 있음 → 압축 해제가 끝난 뒤 같은 명령을 다시 실행하면 이어서 처리")


if __name__ == "__main__":
    sys.exit(main())
