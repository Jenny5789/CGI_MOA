# backend/harmony_client.py
# harmonize_worker.py(자식 프로세스)를 띄워두고 PCTNet 하모나이제이션을 요청하는 쪽.
#
# 설계 원칙은 birefnet_client.py 와 같다: PCTNet 은 '있으면 더 좋은' 보정 단계이지
# 필수 단계가 아니다. 워커를 못 띄우거나 실패하면 None 을 돌려주고, 호출하는 쪽은
# 기존 LAB 색이동 방식으로 합성한다. 이 기능 때문에 합성 자체가 실패하면 안 된다.

import json
import os
import subprocess
import tempfile
import threading
import uuid

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKER_SCRIPT = os.path.join(BASE_DIR, "harmonize_worker.py")
LIBCOM_PYTHON = os.path.abspath(
    os.path.join(BASE_DIR, "..", "venv_libcom", "Scripts", "python.exe")
)

_proc: subprocess.Popen | None = None
_lock = threading.Lock()       # 워커는 하나뿐이라 요청을 직렬화해야 한다
_disabled = False              # 한 번 못 띄우면 매 요청마다 재시도하지 않는다


def _log(msg: str):
    print(f"[harmony_client] {msg}", flush=True)


def _read_json_line(proc: subprocess.Popen, max_skip: int = 50) -> dict | None:
    """
    워커의 응답 한 건을 읽는다. 딸려 있는 라이브러리가 stdout 에 로그를 흘리는 경우가
    있어서, JSON 으로 해석되는 줄이 나올 때까지 건너뛴다.
    """
    for _ in range(max_skip):
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            _log(f"워커 출력 무시: {line[:120]}")
    return None


def _start_worker() -> subprocess.Popen | None:
    global _disabled
    if _disabled:
        return None
    if not os.path.exists(LIBCOM_PYTHON):
        _log(f"venv_libcom 파이썬이 없어 PCTNet 을 건너뜁니다: {LIBCOM_PYTHON}")
        _disabled = True
        return None

    _log("워커 프로세스 시작 (최초 1회 모델 로딩)")
    proc = subprocess.Popen(
        [LIBCOM_PYTHON, WORKER_SCRIPT],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
        text=True, encoding="utf-8", cwd=BASE_DIR,
    )
    ready = _read_json_line(proc)
    if ready is None or not ready.get("ready"):
        _log(f"워커 준비 실패, PCTNet 없이 진행합니다: {ready}")
        proc.kill()
        _disabled = True
        return None

    _log("워커 준비 완료")
    return proc


def _ensure_worker() -> subprocess.Popen | None:
    global _proc
    if _proc is not None and _proc.poll() is None:
        return _proc
    _proc = _start_worker()
    return _proc


def harmonize(composite_rgb: np.ndarray, fg_mask: np.ndarray) -> np.ndarray | None:
    """
    이미 붙여놓은 합성 이미지의 객체 영역 색감을 배경에 맞게 보정한다.

    composite_rgb : 객체를 붙인 뒤의 전체 이미지 (RGB)
    fg_mask       : 그 이미지에서 객체가 차지하는 영역 (0/1 또는 0~255)

    반환은 보정된 RGB 이미지. 실패하면 None (호출하는 쪽이 대체 경로를 쓴다).
    """
    if fg_mask.max() == 0:
        return None

    tmp_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    comp_path = os.path.join(tmp_dir, f"pct_comp_{uid}.png")
    mask_path = os.path.join(tmp_dir, f"pct_mask_{uid}.png")
    out_path = os.path.join(tmp_dir, f"pct_out_{uid}.png")

    try:
        with _lock:
            proc = _ensure_worker()
            if proc is None:
                return None

            cv2.imwrite(comp_path, cv2.cvtColor(composite_rgb, cv2.COLOR_RGB2BGR))
            cv2.imwrite(mask_path, (fg_mask * 255).astype(np.uint8) if fg_mask.max() <= 1 else fg_mask.astype(np.uint8))

            proc.stdin.write(json.dumps({"comp": comp_path, "mask": mask_path, "out": out_path}) + "\n")
            proc.stdin.flush()

            result = _read_json_line(proc)
            if result is None:
                _log("워커가 응답 없이 종료됨")
                return None
            if not result.get("ok"):
                _log(f"보정 실패: {result.get('error')}")
                return None

        harmonized_bgr = cv2.imread(out_path)
        if harmonized_bgr is None:
            return None
        return cv2.cvtColor(harmonized_bgr, cv2.COLOR_BGR2RGB)
    except Exception as e:
        _log(f"보정 중 오류, 기본 합성으로 진행합니다: {e}")
        return None
    finally:
        for p in (comp_path, mask_path, out_path):
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
