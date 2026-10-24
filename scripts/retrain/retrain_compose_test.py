"""AnyDoor 재학습 결과 확인: 새 입력으로 유형 B 5장 합성 (원래 가중치 / 재학습 가중치).

- 합성: 서버 features.composition.AnyDoorComposer 그대로 (float16, save_memory, 크롭 1.3배, 50스텝)
- 새 입력: AnyDoor의 process_pairs만 이 스크립트 안에서 교체 (retrain_dataset.py 학습 재료와 같은 계산, 서버·AnyDoor 코드 수정 없음)
  - 생성 영역 = agnostic-mask (상체 옷 + 팔), 조건 이미지 = 옷 사진 비율 그대로 어깨 기준 배치 (VITON-HD 관절 점)
- 대상: VITON-HD 시험용 유형 B 5장 (아래 CASES), seed 3개씩, 이미 만든 결과는 건너뜀
- 저장: <out_dir>/V??_seed????_<이름>.png, compose_compare.jpg (결과 폴더에 있는 이름을 모두 모아 비교, 첫 seed)

python retrain_compose_test.py <out_dir> original original                 (원래 가중치)
python retrain_compose_test.py <out_dir> step10000 <가중치 .ckpt 경로>     (재학습 가중치)
경로: ANYDOOR_DIR (AnyDoor 폴더), VITON_TEST_DIR (기본 $ANYDOOR_DIR/data/zalando-hd-resized/test)
"""
import gc
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # 저장소 최상위 (features 패키지)
sys.path.insert(1, str(HERE))
import cv2  # noqa: E402

from retrain_dataset import AD, du, placed_hint  # noqa: E402
from retrain_ids import font  # noqa: E402

OUT, NAME, CKPT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
OUT.mkdir(parents=True, exist_ok=True)
VT = Path(os.environ.get("VITON_TEST_DIR", AD / "data" / "zalando-hd-resized" / "test"))
# 유형 B 5장 (10/21 분류): 이름, 인물 사진, 새 상의 사진, 첫 seed (seed 3개 = 첫 seed, +1000, +2000)
CASES = [("V02", "03906_00.jpg", "09303_00.jpg", 1001), ("V28", "07395_00.jpg", "03731_00.jpg", 1027),
         ("V37", "14097_00.jpg", "02649_00.jpg", 1036), ("V50", "00095_00.jpg", "09396_00.jpg", 1049),
         ("V62", "04957_00.jpg", "04523_00.jpg", 1061)]
CROP = 1.3


def load(person_name, cloth_name):
    person = np.array(Image.open(VT / "image" / person_name).convert("RGB"))
    cloth = np.array(Image.open(VT / "cloth" / cloth_name).convert("RGB"))
    cmask = (np.array(Image.open(VT / "cloth-mask" / cloth_name).convert("L")) > 127).astype(np.uint8)
    ag = (np.array(Image.open(VT / "agnostic-mask" / person_name.replace(".jpg", "_mask.png")).convert("L")) > 127).astype(np.uint8)
    k = json.loads((VT / "openpose_json" / person_name.replace(".jpg", "_keypoints.json")).read_text())
    p = np.array(k["people"][0]["pose_keypoints_2d"], np.float32).reshape(-1, 3)
    return person, cloth, cmask, ag, p


def new_input(ref_image, ref_mask, tar_image, tar_mask, p):
    """새 입력 process_pairs: run_inference.py와 같은 출력 키, 생성 영역·조건 이미지만 새 방식"""
    y1, y2, x1, x2 = du.get_bbox_from_mask(ref_mask)
    m3 = np.stack([ref_mask] * 3, -1)
    ref = (ref_image * m3 + 255 * (1 - m3))[y1:y2, x1:x2]
    ref, _ = du.expand_image_mask(ref, ref_mask[y1:y2, x1:x2], ratio=1.2)  # run_inference.py와 같은 1.2배
    ref = cv2.resize(du.pad_to_square(ref, 255).astype(np.uint8), (224, 224))
    H, W = tar_mask.shape
    by1, by2, bx1, bx2 = du.get_bbox_from_mask(tar_mask)
    yc, xc, h, w = 0.5 * (by1 + by2), 0.5 * (bx1 + bx2), CROP * (by2 - by1 + 1), CROP * (bx2 - bx1 + 1)
    crop = du.box2squre(tar_image, (max(0, int(yc - h / 2)), min(H, int(yc + h / 2)), max(0, int(xc - w / 2)), min(W, int(xc + w / 2))))
    hint_big, sil = placed_hint(ref_image, ref_mask, p, H, W)
    collage = tar_image.copy()
    collage[tar_mask > 0] = 0
    collage[sil > 0] = hint_big[sil > 0]
    cy1, cy2, cx1, cx2 = crop
    H1, W1 = cy2 - cy1, cx2 - cx1
    tgt = du.pad_to_square(tar_image[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    col = du.pad_to_square(collage[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    cm = du.pad_to_square(np.stack([tar_mask[cy1:cy2, cx1:cx2]] * 3, -1).astype(np.uint8), pad_value=2).astype(np.uint8)
    H2, W2 = col.shape[:2]
    tgt = cv2.resize(tgt, (512, 512)).astype(np.float32)
    col = cv2.resize(col, (512, 512)).astype(np.float32)
    cm = cv2.resize(cm, (512, 512), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    cm[cm == 2] = -1  # 학습과 같게 정사각형 빈칸은 −1
    return dict(ref=ref.astype(np.float32) / 255, jpg=tgt / 127.5 - 1.0, hint=np.concatenate([col / 127.5 - 1.0, cm[:, :, :1]], -1),
                extra_sizes=np.array([H1, W1, H2, W2]), tar_box_yyxx_crop=np.array(crop))


plan = [(tag, s0, *load(pn, cn)) for tag, pn, cn, s0 in CASES]
todo = [(tag, s) for tag, s0, *_r in plan for s in (s0, s0 + 1000, s0 + 2000) if not (OUT / f"{tag}_seed{s}_{NAME}.png").exists()]
if todo:
    from features.composition import AnyDoorComposer

    composer = AnyDoorComposer()  # 서버와 같은 설정, ANYDOOR_DIR 사용
    ns = composer._load()
    if CKPT != "original":
        from cldm.model import load_state_dict

        sd = load_state_dict(CKPT, location="cpu")
        missing, unexpected = ns["model"].load_state_dict(sd, strict=False)
        print(f"재학습 가중치 불러옴: {CKPT} (빠진 키 {len(missing)}, 남는 키 {len(unexpected)})", flush=True)
        del sd
        gc.collect()
    cur = {}
    ns["process_pairs"] = lambda ref_image, ref_mask, tar_image, tar_mask: new_input(ref_image, ref_mask, tar_image, tar_mask, cur["p"])
    for tag, s0, person, cloth, cmask, ag, p in plan:
        cur["p"] = p
        for s in (s0, s0 + 1000, s0 + 2000):
            path = OUT / f"{tag}_seed{s}_{NAME}.png"
            if path.exists():
                continue
            Image.fromarray(composer.compose(cloth, cmask, person, ag, seed=s)).save(path)
            print(f"{tag} seed {s} ({NAME}) 저장", flush=True)

# 비교 그림 (첫 seed): 원래 사진 | 새 상의 | 새 입력 | 결과 폴더에 있는 이름별 결과 (original 먼저)
names = sorted({f.stem.split("_", 2)[2] for f in OUT.glob(f"{CASES[0][0]}_seed{CASES[0][3]}_*.png")}, key=lambda x: (x != "original", x))
F, FB = font(15), font(19)
W_, H_, GAP = 200, 267, 8
rows = []
for tag, s0, person, cloth, cmask, ag, p in plan:
    view = person.copy()
    view[ag > 0] = (view[ag > 0] * 0.4 + np.array([0, 90, 255]) * 0.6).astype(np.uint8)
    _, sil = placed_hint(cloth, cmask, p, *ag.shape)
    cs, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(view, cs, -1, (0, 220, 0), 4)
    ims = [("원래 사진", person), ("새 상의", cloth), ("새 입력 (파랑 = 생성 영역, 초록 = 옷 그림)", view)] \
        + [(f"새 입력 + {x}", np.array(Image.open(OUT / f"{tag}_seed{s0}_{x}.png").convert("RGB"))) for x in names]
    r = Image.new("RGB", (len(ims) * (W_ + GAP), H_ + 56), "white")
    dr = ImageDraw.Draw(r)
    dr.text((4, 2), f"{tag} (seed {s0})", fill="black", font=FB)
    for j, (t, im) in enumerate(ims):
        dr.text((j * (W_ + GAP) + 2, 30), t, fill="black", font=F)
        r.paste(Image.fromarray(im).resize((W_, H_)), (j * (W_ + GAP), 52))
    rows.append(r)
sheet = Image.new("RGB", (rows[0].width, sum(x.height + 10 for x in rows)), "white")
y = 0
for x in rows:
    sheet.paste(x, (0, y))
    y += x.height + 10
sheet.save(OUT / "compose_compare.jpg", quality=90)
print("저장", OUT / "compose_compare.jpg", flush=True)
