"""원본 복원 후처리: 합성 결과에서 지킬 곳만 쓰고 나머지는 원본 인물 사진으로 되돌린다.

AnyDoor는 착용 영역 주변(크롭 영역)을 통째로 다시 그려 얼굴·머리가 조금씩 바뀐다.
- 착용 영역 상단 경계(세로줄마다 착용 영역 최상단을 이은 선) 위 = 원본, 아래 = 합성 결과
- 합성 결과의 새 상의(SAM2로 찾음)는 경계 위라도 합성 결과 유지 → 어깨 끝 잘림 방지
- 시험: CGI_MOA 작업일지 10/17 ⑪·⑬·⑮ (100건, 얼굴 영역 MAE 5.81 → 0.36, 어깨 끝 잘림 500px 초과 59 → 0건)

물체 기준 원본 복원 2026-11-10, restore_scene·restore_by_object:
- 문제: 위 상단 경계는 사진 속 물체와 무관한 선이라 평평한 배경을 가로지른다. AnyDoor가 다시 그린 배경은 원본보다
  7~15 정도 어둡고 흐려, 경계가 세로로 꺾이는 어깨·팔 옆에 세로 잔상이 생겼다.
  박스 선 보정은 원본 손과 합성 결과의 색 차이를 안쪽으로 퍼뜨려 붉은 얼룩도 만들었다
- 방법: 위치가 아니라 각 픽셀이 무엇인지로 나눈다. SAM2로 원본 사람, 합성 결과 사람, 새 상의, 원래 상의를 찾고
  - 합성 결과에서 가져올 곳: 상단 경계 아래의 합성 결과 사람, 새 상의
  - 원래 사람이 있었는데 합성 결과 사람이 덮지 않은 곳: 원래 사람을 지운 원본 배경 추정으로 채움
  - 나머지 배경·얼굴·머리: 원본 그대로
  원본과 합성 결과가 바뀌는 선이 항상 사람·옷 윤곽에 놓여 배경끼리 맞닿는 곳이 없다. 박스 선 보정은 쓰지 않는다
- 시험: 11/10 VM 합성 6건의 모델 원래 결과, 다시 그린 정사각형 안 배경 중 원본 그대로인 비율 85.5~91.3% → 98.1~99.2%,
  잔상·붉은 얼룩 육안 확인 없음. 사람을 찾지 못하면 기존 상단 경계 방식으로 처리
"""
from functools import partial

import cv2
import numpy as np

from .seam import fix_seam

BAND = 20           # 블렌딩 폭: 경계 위 이만큼은 원본과 합성 결과를 섞음 (px)
PERSON_PAD = 0.10   # 사람 찾기 박스: 합성 영역 좌우로 사진 너비의 이 비율만큼 넓히고 위아래는 사진 전체
EDGE_KERNEL = 11    # 원래 사람 영역을 이 크기 커널로 넓혀 지움: SAM2가 놓친 테두리·그림자 5px까지 포함
HOLE_KERNEL = 9     # 빈자리 부드러운 테두리를 배경 위에 두기 위한 확장 커널
OLD_GARMENT_NEAR = 31  # 원래 상의는 합성 영역에서 이 커널 반경 안 조각만 지움
# (실험용) 새 상의 유지 범위 제한: 상단 경계 위 최대 px, None = 제한 없음. 서버는 항상 None으로 쓴다.
# 10/17 100건 시험에서 60·100·150px 모두 얼굴 보호 효과가 없었고, 제한이 없을 때 상의 잘림이 0건이라 제한하지 않기로 했다.
# 시험을 다시 해 볼 수 있게 restore_original(reach=...) 매개변수와 이 분기만 남겨 둔다
GARMENT_REACH = None
GARMENT_RATIO = (0.3, 2.0)  # 찾은 새 상의 크기 / 착용 영역 크기가 이 범위 밖이면 찾기 실패로 봄


def top_boundary(area):
    """세로줄마다 착용 영역 최상단 y. 착용 영역이 없는 세로줄은 가장 가까운 세로줄 값 (np.interp가 양 끝 값 유지)"""
    cols = np.where(area.any(axis=0))[0]
    tops = np.argmax(area[:, cols], axis=0)
    return np.interp(np.arange(area.shape[1]), cols, tops)


def _ramp(area, offset, band):
    """경계(상단 경계 - offset) 아래 1, 그 위 band px에서 0으로 줄어드는 비율"""
    ys = np.arange(area.shape[0])[:, None]
    edge = top_boundary(area)[None, :] - offset
    return np.clip((ys - (edge - band)) / band, 0, 1).astype(np.float32)


def find_garment(result, area, extract=None):
    """합성 결과에서 새 상의 영역(0/1)을 SAM2로 찾는다. 착용 영역을 감싼 박스(3% 여유)를 프롬프트로 사용.
    찾은 크기가 GARMENT_RATIO 범위 밖이면 None (찾기 실패 → 상단 경계만으로 원본 복원)
    extract: 이미지 분할 함수. 비우면 이 프로세스의 SAM2, 웹 서비스 서버는 모델 서버 호출 함수 전달"""
    if extract is None:
        from features.object_extraction import extract_object as extract

    h, w = area.shape
    ys, xs = np.where(area)
    pad = int(0.03 * max(h, w))
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
    try:
        garment = extract(result, box=box)
    except RuntimeError:  # 빈 마스크
        return None
    ratio = garment.sum() / max(area.sum(), 1)
    return garment if GARMENT_RATIO[0] <= ratio <= GARMENT_RATIO[1] else None


def restore_original(person, result, area, garment=None, band=BAND, reach=GARMENT_REACH):
    """원본 복원 결과(RGB uint8)를 돌려준다.

    person, result: np.uint8 (H, W, 3) RGB, 같은 크기 (원본 인물 사진, 합성 결과)
    area          : np.uint8 (H, W) 0/1 착용 영역
    garment       : np.uint8 (H, W) 0/1 합성 결과의 새 상의 영역 (find_garment), None이면 상단 경계만 사용
    reach         : (실험용) 새 상의를 상단 경계 위 몇 px까지 유지할지, None = 제한 없음 (GARMENT_REACH 설명 참고). 서버는 기본값(None)으로 부른다
    """
    weight = _ramp(area, 0, band)  # 1 = 합성 결과, 0 = 원본
    if garment is not None:
        soft = cv2.GaussianBlur(cv2.dilate(garment.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(np.float32), (0, 0), 3)
        if reach is not None:
            soft = soft * _ramp(area, reach, band)  # 경계 위 reach px 이내만
        weight = np.maximum(weight, soft)
    weight = weight[..., None]
    out = result.astype(np.float32) * weight + person.astype(np.float32) * (1 - weight)
    return out.round().clip(0, 255).astype(np.uint8)


# ---------- 물체 기준 원본 복원 ----------

def _soft(mask, sigma=1.2):
    """0/1 영역의 가장자리만 부드럽게 한 0~1 비율. 경계 계단 현상 방지용"""
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)


def _grow(mask, k):
    return cv2.dilate(mask.astype(np.uint8), np.ones((k, k), np.uint8)) > 0


def find_person(image, area, extract, image_key=None):
    """사진 속 사람 전체 영역(0/1)을 SAM2로 찾는다. 합성 영역 좌우로 PERSON_PAD만큼 넓히고 위아래는 사진 전체인 박스와
    합성 영역 안쪽에서 가장 깊은 점 하나를 프롬프트로 사용. 찾은 영역이 합성 영역의 절반 이상을 덮지 못하면 None.
    11/10 박스만 쓴 시험에서 합성 영역이 큰 사각형인 사진은 배경을 사람으로 골라 실패, 점을 더해 합성 영역 덮음 0.16 → 0.80"""
    h, w = area.shape
    ys, xs = np.where(area)
    pad = int(PERSON_PAD * w)
    box = (max(xs.min() - pad, 0), 0, min(xs.max() + pad, w), h)
    dist = cv2.distanceTransform(area.astype(np.uint8), cv2.DIST_L2, 5)
    y, x = np.unravel_index(np.argmax(dist), dist.shape)
    try:
        person = extract(image, points=[(int(x), int(y))], box=box, image_key=image_key)
    except RuntimeError:  # 빈 마스크
        return None
    return person if (person & area).sum() >= 0.5 * area.sum() else None


def find_old_garment(person, area, extract, image_key=None):
    """원본 사진의 원래 상의 영역(0/1)을 SAM2로 찾는다. 합성 영역을 감싼 박스와 합성 영역 안쪽에서 가장 깊은 점 하나를 프롬프트로 사용.
    찾은 영역의 90% 이상이 합성 영역 안이고 크기가 합성 영역의 0.2~1.3배일 때만 사용, 아니면 None.
    11/10 시험에서 조건을 0.7로 두자 얼굴까지 상의로 잡혀 지워진 사례가 있어 엄격하게 둔다"""
    h, w = area.shape
    dist = cv2.distanceTransform(area.astype(np.uint8), cv2.DIST_L2, 5)
    y, x = np.unravel_index(np.argmax(dist), dist.shape)
    ys, xs = np.where(area)
    pad = int(0.03 * max(h, w))
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
    try:
        garment = extract(person, points=[(int(x), int(y))], box=box, image_key=image_key)
    except RuntimeError:
        return None
    inside = (garment & area).sum() / max(garment.sum(), 1)
    ratio = garment.sum() / max(area.sum(), 1)
    return garment if inside >= 0.9 and 0.2 <= ratio <= 1.3 else None


def restore_by_object(person, result, area, person_mask, result_person, garment=None, old_garment=None, band=BAND):
    """물체 기준 원본 복원 결과(RGB uint8)를 돌려준다.

    person_mask  : 원본 사진의 사람 영역 0/1 (find_person)
    result_person: 합성 결과의 사람 영역 0/1 (find_person)
    garment      : 합성 결과의 새 상의 영역 0/1 (find_garment), 없으면 None
    old_garment  : 원본 사진의 원래 상의 영역 0/1 (find_old_garment), 없으면 None
    """
    h, w = area.shape
    below = _ramp(area, 0, band)  # 1 = 상단 경계 아래, 위로 band px 동안 0으로. 얼굴·머리는 원본 유지
    new_garment = garment if garment is not None else np.zeros_like(area)
    take = ((result_person > 0) & (below > 0)) | (new_garment > 0)  # 합성 결과에서 가져올 곳

    # 원래 사람 중 합성 결과 사람이 덮지 않은 곳은 배경으로 바꿈
    core = _grow(person_mask, EDGE_KERNEL) & (below > 0) & ~take
    if old_garment is not None:  # 합성 영역 밖으로 삐져나온 원래 상의 조각
        core |= _grow(old_garment & _grow(area, OLD_GARMENT_NEAR), 5) & ~take
    hole = _grow(core, HOLE_KERNEL) & ~take

    base = person.astype(np.float32)
    if hole.any():
        # 원본 배경 추정: 원래 사람 전체와 빈자리를 지우고 주변 배경으로 채움. 배경은 저주파라 절반 크기에서 계산
        erase = _grow(_grow(person_mask, 15) | hole, 3)
        small = cv2.resize(person, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
        erase_small = (cv2.resize(erase.astype(np.uint8), (w // 2, h // 2), interpolation=cv2.INTER_AREA) > 0).astype(np.uint8)
        background = cv2.resize(cv2.inpaint(small, erase_small, 7, cv2.INPAINT_TELEA), (w, h), interpolation=cv2.INTER_CUBIC)
        # 원래 사람 자리는 완전히 배경, 부드러운 테두리는 배경 위에만 둔다
        fill = np.maximum(_soft(hole, 2.0), core.astype(np.float32))[..., None]
        base = base * (1 - fill) + background.astype(np.float32) * fill

    alpha = np.clip(np.maximum(_soft(result_person) * below, _soft(new_garment)), 0, 1)[..., None]
    out = result.astype(np.float32) * alpha + base * (1 - alpha)
    return out.round().clip(0, 255).astype(np.uint8)


def restore_scene(person, result, area, extract, crop_box=None, person_key=None, result_key=None):
    """원본 복원 진입점. 반환: (결과 RGB uint8, 기록용 정보 dict)

    extract   : 이미지 분할 함수, 웹 서비스 서버는 backend/model_client.extract
    crop_box  : 다시 그린 정사각형 위치. 사람을 찾지 못해 기존 상단 경계 방식으로 처리할 때만 박스 선 보정에 사용
    person_key, result_key: SAM2 이미지 인코딩 재사용 키. 같은 사진을 연달아 분할할 때 인코딩을 한 번만 한다
    """
    ext_result = partial(extract, image_key=result_key)
    ext_person = partial(extract, image_key=person_key)
    garment = find_garment(result, area, extract=ext_result)
    result_person = find_person(result, area, ext_result)
    person_mask = find_person(person, area, ext_person)
    info = {"garment_found": garment is not None}
    if person_mask is None or result_person is None:
        fixed = fix_seam(person, result, crop_box) if crop_box is not None else result
        info.update(method="boundary", seam_fix=crop_box is not None)
        return restore_original(person, fixed, area, garment), info
    old_garment = find_old_garment(person, area, ext_person)
    info.update(method="object", seam_fix=False, old_garment_found=old_garment is not None)
    return restore_by_object(person, result, area, person_mask, result_person, garment, old_garment), info
