"""원본 복원 후처리: 합성 결과에서 지킬 곳만 쓰고 나머지는 원본 인물 사진으로 되돌린다.

AnyDoor는 착용 영역 주변(크롭 영역)을 통째로 다시 그려 얼굴·머리가 조금씩 바뀐다.
- 착용 영역 상단 경계(세로줄마다 착용 영역 최상단을 이은 선) 위 = 원본, 아래 = 합성 결과
- 합성 결과의 새 상의(SAM2로 찾음)는 경계 위라도 합성 결과 유지 → 어깨 끝 잘림 방지
- 시험: CGI_MOA 작업일지 10/17 ⑪·⑬·⑮ (100건, 얼굴 영역 MAE 5.81 → 0.36, 어깨 끝 잘림 500px 초과 59 → 0건)
"""
import cv2
import numpy as np

BAND = 20           # 블렌딩 폭: 경계 위 이만큼은 원본과 합성 결과를 섞음 (px)
GARMENT_REACH = None  # 새 상의 유지 범위 제한 (상단 경계 위 최대 px, None = 제한 없음. 10/17 100건: 60·100·150px 모두 얼굴 보호 효과 없음, 제한 없음일 때 상의 잘림 0건)
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


def find_garment(result, area):
    """합성 결과에서 새 상의 영역(0/1)을 SAM2로 찾는다. 착용 영역을 감싼 박스(3% 여유)를 프롬프트로 사용.
    찾은 크기가 GARMENT_RATIO 범위 밖이면 None (찾기 실패 → 상단 경계만으로 원본 복원)"""
    from features.object_extraction import extract_object

    h, w = area.shape
    ys, xs = np.where(area)
    pad = int(0.03 * max(h, w))
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
    try:
        garment = extract_object(result, box=box)
    except RuntimeError:  # 빈 마스크
        return None
    ratio = garment.sum() / max(area.sum(), 1)
    return garment if GARMENT_RATIO[0] <= ratio <= GARMENT_RATIO[1] else None


def restore_original(person, result, area, garment=None, band=BAND, reach=GARMENT_REACH):
    """원본 복원 결과(RGB uint8)를 돌려준다.

    person, result: np.uint8 (H, W, 3) RGB, 같은 크기 (원본 인물 사진, 합성 결과)
    area          : np.uint8 (H, W) 0/1 착용 영역
    garment       : np.uint8 (H, W) 0/1 합성 결과의 새 상의 영역 (find_garment), None이면 상단 경계만 사용
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
