"""명세 5-1~5-3 합성.

- POST /api/compose        : 합성 요청. 작업 번호를 바로 돌려주고 합성은 뒤에서 진행 (명세 5-1)
- GET  /api/jobs/{job_id}  : 진행 확인 (명세 5-2)
- GET  /api/results/{id}   : 결과 받기 (명세 5-3)

처리 방식
- 합성 전담 일꾼(스레드) 하나가 들어온 순서대로 한 번에 한 장씩 처리
- GPU는 추출과 같은 GPU_LOCK으로 차례를 지킨다 (합성 중에 들어온 추출 요청은 합성이 끝날 때까지 기다림)
- AnyDoor는 features/composition의 compose를 그대로 쓴다 (50스텝, float16 + save_memory)
- 임시: 로그인 확인 없음, 작업·결과는 storage/jobs, storage/results에 파일로 저장
"""
import io
import json
import logging
import queue
import random
import threading
import uuid

import numpy as np
from fastapi import APIRouter, File, Form, UploadFile
from PIL import Image, UnidentifiedImageError

from backend.config import EXTRACTIONS_DIR, IMAGES_DIR, JOBS_DIR, MAX_UPLOAD_BYTES, RESULTS_DIR
from backend.errors import ApiError
from backend.gpu import GPU_LOCK
from backend.storage import _ID, load_extraction_info, load_image_info, now_kst

router = APIRouter()
log = logging.getLogger("moa.compose")

THUMB_WIDTH = 400

_jobs = {}            # job_id -> 작업 정보 (메모리)
_waiting = []         # 대기 중인 job_id (순서대로)
_lock = threading.Lock()
_queue = queue.Queue()
_worker = None


# ---------- 작업 기록 ----------

def _save_job(job):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    (JOBS_DIR / f"{job['job_id']}.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")


def _update(job_id, **changes):
    with _lock:
        job = _jobs[job_id]
        job.update(changes)
        snapshot = dict(job)
    _save_job(snapshot)


def _public(job):
    """명세 5-2 모양으로"""
    with _lock:
        position = _waiting.index(job["job_id"]) + 1 if job["job_id"] in _waiting else 0
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "queue_position": position,
        "result_id": job["result_id"],
        "error": job["error"],
    }


# ---------- 서버 켤 때 예열 ----------

def start_warmup():
    """AnyDoor를 미리 불러오고 2스텝 합성을 한 번 돌린다 (뒤에서 진행, 서버는 바로 응답).
    예열 중에 들어온 합성·추출은 GPU_LOCK에서 기다렸다가 예열이 끝나면 처리된다."""
    def run():
        from features.composition import warmup
        print("[MOA] AnyDoor 예열 시작 (모델 불러오기 + 2스텝 합성, 1~2분)", flush=True)  # 서버 창에서 바로 보이게 print
        try:
            with GPU_LOCK:
                warmup()
            print("[MOA] AnyDoor 예열 끝: 합성 준비 완료", flush=True)
        except Exception:  # 예열이 실패해도 서버는 계속 돈다 (첫 합성 때 다시 불러온다)
            log.exception("AnyDoor 예열 실패")

    threading.Thread(target=run, name="compose-warmup", daemon=True).start()


# ---------- 합성 일꾼 ----------

def _ensure_worker():
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_work_loop, name="compose-worker", daemon=True)
            _worker.start()


def _work_loop():
    while True:
        job_id = _queue.get()
        try:
            _run(job_id)
        except Exception as exc:  # 한 작업이 실패해도 일꾼은 계속 돈다
            log.exception("합성 실패: %s", job_id)
            _update(job_id, status="failed", error={"code": "COMPOSE_FAILED", "message": f"합성 중 오류가 발생했습니다: {exc}"})
        finally:
            _queue.task_done()


def _run(job_id):
    from features.composition import compose  # AnyDoor는 서버 켤 때 예열에서 불러온다 (예열을 껐으면 첫 합성 때)

    with _lock:
        _waiting.remove(job_id)
        job = dict(_jobs[job_id])
    _update(job_id, status="running", progress=0.0, started_at=now_kst())

    ext = load_extraction_info(job["extraction_id"])
    garment = load_image_info(ext["image_id"])
    person = load_image_info(job["person_image_id"])

    ref = np.array(Image.open(IMAGES_DIR / garment["filename"]).convert("RGB"))
    ref_mask = (np.array(Image.open(EXTRACTIONS_DIR / ext["mask"]).convert("L")) > 127).astype(np.uint8)
    tar = np.array(Image.open(IMAGES_DIR / person["filename"]).convert("RGB"))
    tar_mask = (np.array(Image.open(JOBS_DIR / job["area_mask"]).convert("L")) > 127).astype(np.uint8)

    def on_progress(p):
        _update(job_id, progress=round(min(p, 1.0), 3))

    with GPU_LOCK:
        result = compose(ref, ref_mask, tar, tar_mask, seed=job["seed"], on_progress=on_progress)

    result_id = "res_" + uuid.uuid4().hex[:12]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(result)
    img.save(RESULTS_DIR / f"{result_id}.png")
    thumb = img.copy()
    thumb.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 4))
    thumb.save(RESULTS_DIR / f"{result_id}_thumb.jpg", quality=90)

    record = {
        "result_id": result_id,
        "image_url": f"/api/files/{result_id}.png",
        "thumb_url": f"/api/files/{result_id}_thumb.jpg",
        "created_at": now_kst(),
        "saved": False,
        "favorite": False,
        "garment_image_id": ext["image_id"],
        "person_image_id": job["person_image_id"],
        # 아래는 명세 밖 기록 (재현·분석용)
        "job_id": job_id,
        "extraction_id": job["extraction_id"],
        "seed": job["seed"],
    }
    (RESULTS_DIR / f"{result_id}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    _update(job_id, status="done", progress=1.0, result_id=result_id, finished_at=now_kst())


# ---------- 주소 ----------

@router.post("/api/compose")
async def request_compose(
    extraction_id: str = Form(...),
    person_image_id: str = Form(...),
    area_mask: UploadFile = File(...),
):
    load_extraction_info(extraction_id)          # 없으면 404
    person = load_image_info(person_image_id)    # 없으면 404

    data = await area_mask.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(400, "INVALID_AREA_MASK", "입힐 영역 그림이 너무 큽니다.")
    try:
        mask_img = Image.open(io.BytesIO(data))
        mask_img.load()
    except (UnidentifiedImageError, OSError):
        raise ApiError(400, "INVALID_AREA_MASK", "입힐 영역 그림을 읽을 수 없습니다.")

    # 명세 5-1: 인물 사진과 같은 비율이면 되고, 크기는 서버가 원본에 맞춘다 (칠한 곳 255)
    mask_img = mask_img.convert("L").resize((person["width"], person["height"]), Image.NEAREST)
    mask = (np.array(mask_img) > 127).astype(np.uint8)
    if mask.sum() == 0:
        raise ApiError(400, "EMPTY_AREA", "입힐 영역을 칠해 주세요.")

    job_id = "job_" + uuid.uuid4().hex[:12]
    area_name = f"{job_id}_area.png"
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask * 255).save(JOBS_DIR / area_name)

    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "result_id": None,
        "error": None,
        "extraction_id": extraction_id,
        "person_image_id": person_image_id,
        "area_mask": area_name,
        "seed": random.randint(0, 2 ** 31 - 1),
        "created_at": now_kst(),
    }
    with _lock:
        _jobs[job_id] = job
        _waiting.append(job_id)
    _save_job(job)
    _ensure_worker()
    _queue.put(job_id)

    public = _public(job)
    return {"job_id": job_id, "status": public["status"], "queue_position": public["queue_position"]}


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with _lock:
        job = dict(_jobs[job_id]) if job_id in _jobs else None
    if job is None:
        # 서버를 다시 켜면 메모리 기록은 사라진다. 파일 기록이 있으면 그것을 보여 준다
        path = JOBS_DIR / f"{job_id}.json"
        if not _ID.match(job_id) or not path.is_file():
            raise ApiError(404, "JOB_NOT_FOUND", "작업을 찾을 수 없습니다.")
        job = json.loads(path.read_text(encoding="utf-8"))
        if job["status"] in ("queued", "running"):
            job["status"] = "failed"
            job["error"] = {"code": "SERVER_RESTARTED", "message": "서버가 다시 시작되어 작업이 중단되었습니다. 다시 요청해 주세요."}
    return _public(job)


@router.get("/api/results/{result_id}")
def get_result(result_id: str):
    path = RESULTS_DIR / f"{result_id}.json"
    if not _ID.match(result_id) or not path.is_file():
        raise ApiError(404, "RESULT_NOT_FOUND", "결과를 찾을 수 없습니다.")
    record = json.loads(path.read_text(encoding="utf-8"))
    keys = ("result_id", "image_url", "thumb_url", "created_at", "saved", "favorite", "garment_image_id", "person_image_id")
    return {k: record[k] for k in keys}
