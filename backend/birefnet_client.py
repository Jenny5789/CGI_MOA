# backend/birefnet_client.py
# birefnet_worker.py(자식 프로세스)를 띄워두고 재분할을 요청하는 쪽.
#
# 설계 원칙: BiRefNet 은 '있으면 더 좋은' 개선 단계이지 필수 단계가 아니다.
# 워커를 못 띄우거나 처리가 실패하면 None 을 돌려주고, 호출하는 쪽은
# SAM 마스크를 그대로 쓴다. 즉 이 기능 때문에 추출 자체가 실패하는 일은 없어야 한다.

import json
import os
import subprocess
import sys
import tempfile
import threading
import uuid

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKER_SCRIPT = os.path.join(BASE_DIR, "birefnet_worker.py")
# BiRefNet 은 torch 2.6 이 필요해서 백엔드(torch 2.0)와 다른 가상환경을 쓴다
LIBCOM_PYTHON = os.path.abspath(
    os.path.join(BASE_DIR, "..", "venv_libcom", "Scripts", "python.exe")
)

_proc: subprocess.Popen | None = None
_lock = threading.Lock()       # 워커는 하나뿐이라 요청을 직렬화해야 한다
_disabled = False              # 한 번 못 띄우면 매 요청마다 재시도하지 않는다


def _log(msg: str):
    print(f"[birefnet_client] {msg}", flush=True)


def _start_worker() -> subprocess.Popen | None:
    global _disabled
    if _disabled:
        return None
    if not os.path.exists(LIBCOM_PYTHON):
        _log(f"venv_libcom 파이썬이 없어 BiRefNet 을 건너뜁니다: {LIBCOM_PYTHON}")
        _disabled = True
        return None

    _log("워커 프로세스 시작 (최초 1회 모델 로딩, 수십 초 걸릴 수 있음)")
    proc = subprocess.Popen(
        [LIBCOM_PYTHON, WORKER_SCRIPT],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
        text=True, encoding="utf-8", cwd=BASE_DIR,
    )
    ready = proc.stdout.readline()          # 모델 로딩이 끝나면 준비 신호가 온다
    try:
        if not json.loads(ready).get("ready"):
            raise RuntimeError(ready)
    except Exception as e:
        _log(f"워커 준비 실패, BiRefNet 없이 진행합니다: {e}")
        proc.kill()
        _disabled = True
        return None

    _log("워커 준비 완료")
    return proc


def _ensure_worker() -> subprocess.Popen | None:
    """워커가 죽어 있으면 한 번 되살린다."""
    global _proc
    if _proc is not None and _proc.poll() is None:
        return _proc
    _proc = _start_worker()
    return _proc


def refine_mask(image_rgb: np.ndarray, mask: np.ndarray, margin_ratio: float = 0.15) -> np.ndarray | None:
    """
    SAM 마스크의 바운딩박스 주변을 BiRefNet 으로 다시 분할해 부드러운 알파(0~255)를 얻는다.
    실패하면 None (호출하는 쪽에서 SAM 마스크를 그대로 쓰면 된다).

    margin_ratio: 크롭할 때 바운딩박스 바깥으로 둘 여유. 마스크가 실제 물체보다
                  작게 잡혔을 때(반사 재질에서 경계가 잘리는 경우 등) 잘린 부분까지
                  크롭 안에 들어와야 BiRefNet 이 그걸 찾아낼 기회가 생긴다.
    """
    x, y, bw, bh = cv2.boundingRect(mask.astype(np.uint8))
    if bw == 0 or bh == 0:
        return None

    h, w = mask.shape[:2]
    mx, my = int(bw * margin_ratio), int(bh * margin_ratio)
    bbox = [max(0, x - mx), max(0, y - my), min(w, x + bw + mx), min(h, y + bh + my)]

    tmp_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    src_path = os.path.join(tmp_dir, f"birefnet_src_{uid}.png")
    out_path = os.path.join(tmp_dir, f"birefnet_out_{uid}.png")

    try:
        with _lock:
            proc = _ensure_worker()
            if proc is None:
                return None

            cv2.imwrite(src_path, cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
            proc.stdin.write(json.dumps({"src": src_path, "bbox": bbox, "out": out_path}) + "\n")
            proc.stdin.flush()

            reply = proc.stdout.readline()
            if not reply:
                _log("워커가 응답 없이 종료됨")
                return None
            result = json.loads(reply)
            if not result.get("ok"):
                _log(f"재분할 실패: {result.get('error')}")
                return None

        alpha = cv2.imread(out_path, cv2.IMREAD_GRAYSCALE)
        return alpha
    except Exception as e:
        _log(f"재분할 중 오류, SAM 마스크로 진행합니다: {e}")
        return None
    finally:
        for p in (src_path, out_path):
            try:
                os.remove(p)
            except OSError:
                pass


def shutdown():
    """서버 종료 시 워커도 같이 정리한다(GPU 메모리 반환)."""
    global _proc
    if _proc is not None and _proc.poll() is None:
        try:
            _proc.stdin.write("\n")
            _proc.stdin.flush()
            _proc.wait(timeout=5)
        except Exception:
            _proc.kill()
    _proc = None
