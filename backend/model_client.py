"""모델 호출 계층. 이미지 분할·이미지 합성·예열을 한 곳에서 처리한다.

- 환경 변수 MODEL_SERVER_URL 비움: 이 서버 프로세스에서 SAM2·이미지 합성 모델 직접 실행. 기존 방식
- MODEL_SERVER_URL 설정: 모델 추론 서버 model_server/app.py로 HTTP 요청. 이 서버는 모델을 적재하지 않음
  - MODEL_TOKEN: 모델 서버에 같은 값이 설정된 경우 요청 헤더 X-Model-Token으로 전달
  - 이미지는 디코딩한 배열을 PNG로 전송. 손실 압축 없이 직접 실행과 같은 입력 보장
  - 합성 진행률: 합성 요청 중 /progress를 주기적으로 조회해 on_progress로 전달
- 직접 실행 시 GPU 작업은 GPU_LOCK으로 한 번에 하나씩. 모델 서버 방식은 모델 서버가 순서 관리
"""
import io
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

from backend.gpu import GPU_LOCK, release_cached_memory

MODEL_SERVER_URL = (os.environ.get("MODEL_SERVER_URL") or "").rstrip("/") or None
MODEL_TOKEN = os.environ.get("MODEL_TOKEN") or None
REMOTE = MODEL_SERVER_URL is not None
PROGRESS_INTERVAL = 0.5  # 합성 진행률 조회 간격, 초
WARMUP_TIMEOUT = 900  # 모델 서버 준비 대기 한도, 초


class ModelServerError(Exception):
    """모델 서버 연결 실패, 준비 전, 처리 오류"""


# ---------- HTTP ----------

def _headers():
    return {"X-Model-Token": MODEL_TOKEN} if MODEL_TOKEN else {}


def _png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _request(method, path, data=None, files=None, timeout=60):
    """모델 서버 요청. 반환: 상태 코드, 본문, 헤더"""
    url = MODEL_SERVER_URL + path
    headers = _headers()
    body = None
    if method == "POST":
        b = uuid.uuid4().hex
        parts = []
        for k, v in (data or {}).items():
            if v is not None:
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, content in (files or {}).items():
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{k}.png"\r\n'
                         f"Content-Type: image/png\r\n\r\n".encode() + content + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={b}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise ModelServerError(f"모델 서버 연결 실패: {MODEL_SERVER_URL}, {e}") from e


def _check(status, body, what):
    if status != 200:
        detail = body.decode("utf-8", "replace")[:300]
        raise ModelServerError(f"모델 서버 {what} 오류 {status}: {detail}")


def server_health():
    status, body, _ = _request("GET", "/health", timeout=10)
    _check(status, body, "상태 확인")
    return json.loads(body)


# ---------- 이미지 분할 ----------

def extract(image_rgb, points=None, neg_points=None, box=None, image_key=None):
    """SAM2 이미지 분할. 반환: uint8 0/1 마스크. 빈 마스크는 RuntimeError, extract_object와 같은 규칙"""
    if not REMOTE:
        from features.object_extraction import extract_object

        with GPU_LOCK:
            try:
                return extract_object(image_rgb, points=points, neg_points=neg_points, box=box, image_key=image_key)
            finally:
                release_cached_memory()

    data = {
        "points": json.dumps([list(map(int, p)) for p in points]) if points else None,
        "neg_points": json.dumps([list(map(int, p)) for p in neg_points]) if neg_points else None,
        "box": json.dumps(list(map(int, box))) if box is not None else None,
        "image_key": image_key,
    }
    status, body, _ = _request("POST", "/extract", data=data, files={"image": _png(image_rgb)}, timeout=120)
    if status == 422:
        raise RuntimeError("빈 마스크가 생성되었습니다.")
    _check(status, body, "이미지 분할")
    return (np.array(Image.open(io.BytesIO(body)).convert("L")) > 127).astype(np.uint8)


# ---------- 이미지 합성 ----------

def compose(ref, ref_mask, tar, tar_mask, seed=None, on_progress=None, shape_control=False, refine=False):
    """이미지 합성. 반환: 결과 RGB 배열, 다시 그린 정사각형 위치 위·아래·왼쪽·오른쪽"""
    if not REMOTE:
        from features.composition import compose as local_compose, last_crop_box

        with GPU_LOCK:
            try:
                result = local_compose(ref, ref_mask, tar, tar_mask, seed=seed, on_progress=on_progress,
                                       shape_control=shape_control, refine=refine)
                return result, last_crop_box()
            finally:
                release_cached_memory()

    done = threading.Event()

    def poll():
        # 합성 요청이 끝날 때까지 모델 서버 진행률을 화면 진행률로 전달
        while not done.wait(PROGRESS_INTERVAL):
            try:
                status, body, _ = _request("GET", "/progress", timeout=5)
                p = json.loads(body).get("progress") if status == 200 else None
                if p is not None and on_progress:
                    on_progress(p)
            except Exception:  # 진행률 조회 실패는 합성 결과에 영향 없음
                pass

    poller = threading.Thread(target=poll, name="model-progress", daemon=True)
    poller.start()
    try:
        files = {"garment": _png(ref), "garment_mask": _png(ref_mask * 255), "person": _png(tar), "area": _png(tar_mask * 255)}
        data = {"seed": seed, "shape_control": str(bool(shape_control)).lower(), "refine": str(bool(refine)).lower()}
        status, body, headers = _request("POST", "/compose", data=data, files=files, timeout=900)
    finally:
        done.set()
    _check(status, body, "이미지 합성")
    result = np.array(Image.open(io.BytesIO(body)).convert("RGB"))
    crop = tuple(int(v) for v in headers["X-Crop-Box"].split(","))
    return result, crop


def find_garment(result, area):
    """합성 결과의 새 상의 영역 찾기. 원본 복원 후처리용, 이미지 분할은 이 계층의 extract 사용"""
    from features.composition import find_garment as _find

    return _find(result, area, extract=extract)


# ---------- 예열 ----------

def warmup(set_state):
    """직접 실행: 이미지 합성 모델 적재와 2스텝 합성. 모델 서버: /health가 ready가 될 때까지 대기.
    set_state: 'done' 또는 'failed'를 받는 함수"""
    if not REMOTE:
        from features.composition import warmup as local_warmup

        with GPU_LOCK:
            local_warmup()
        set_state("done")
        return

    deadline = time.time() + WARMUP_TIMEOUT
    while time.time() < deadline:
        try:
            state = server_health().get("status")
            if state == "ready":
                set_state("done")
                return
            if state == "failed":
                break
        except ModelServerError:  # 모델 서버가 아직 켜지지 않은 경우 계속 대기
            pass
        time.sleep(3)
    set_state("failed")
