"""MOA 모델 추론 서버.

SAM2 이미지 분할과 AnyDoor 기반 이미지 합성 모델을 HTTP로 제공하는 GPU 전용 서버.
웹 서비스 서버는 모델을 직접 적재하지 않고 이 서버에 요청을 보낸다.

- GET  /health  : 적재 상태, 가중치 파일, GPU 정보
- POST /extract : 이미지 분할. 이미지 파일 + 포함 점·제외 점·상자 → 0/255 마스크 PNG
                  image_key가 직전 요청과 같으면 SAM2 이미지 인코딩 생략. 빈 마스크는 422 EMPTY_MASK
- POST /compose : 이미지 합성. 상품 사진·상품 마스크·모델 사진·합성 영역 → 결과 PNG
                  헤더 X-Crop-Box에 다시 그린 정사각형 위치 위·아래·왼쪽·오른쪽
- GET  /progress: 진행 중인 합성의 DDIM 스텝 진행률 0~1, 합성 중이 아니면 null
- 서버 시작 시 별도 스레드에서 SAM2·이미지 합성 모델 적재와 예열 진행, 완료 전 요청은 503
- GPU 작업은 GPU_LOCK으로 한 번에 하나씩 처리. 요청 처리 함수는 동기 함수라 별도 작업 스레드에서 실행되어 합성 중에도 /health 응답 가능
- 환경 변수
  - MODEL_TOKEN: 설정 시 요청 헤더 X-Model-Token 일치 요청만 허용
  - MODEL_SAVE_MEMORY: 1이면 부품 단위 GPU 적재, VRAM 10GB 미만 GPU용
  - ANYDOOR_DIR, ANYDOOR_CKPT, SAM2_CHECKPOINT: 모델 코드·가중치 위치
  - UPSCALE_CKPT: 초해상도 가중치 위치, 파일이 없으면 초해상도 없이 합성
"""
import json
import os
import threading
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

TOKEN = os.environ.get("MODEL_TOKEN") or None
SAVE_MEMORY = os.environ.get("MODEL_SAVE_MEMORY", "0") == "1"

GPU_LOCK = threading.Lock()
STATE = {"status": "loading", "error": None, "load_sec": None}
MODELS = {}
PROGRESS = {"progress": None}  # 진행 중인 합성의 스텝 진행률, 웹 서비스 서버가 주기적으로 조회



def _release():
    import torch

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _load_models():
    """SAM2·이미지 합성 모델 적재와 예열. 서버 시작 직후 별도 스레드에서 1회 실행"""
    t0 = time.time()
    try:
        from features.composition.anydoor_composer import AnyDoorComposer
        from features.object_extraction.sam2_extractor import Sam2Extractor

        with GPU_LOCK:
            sam2 = Sam2Extractor()
            sam2._load()
            print(f"[모델 서버] SAM2 적재 완료 {time.time() - t0:.1f}초", flush=True)
            composer = AnyDoorComposer(save_memory=SAVE_MEMORY)
            composer.warmup(steps=2)
            _release()
        MODELS.update(sam2=sam2, composer=composer)
        STATE.update(status="ready", load_sec=round(time.time() - t0, 1))
        print(f"[모델 서버] 이미지 합성 모델 적재·예열 완료 {time.time() - t0:.1f}초", flush=True)
    except Exception as e:  # 실패 원인을 /health로 확인할 수 있게 보관
        STATE.update(status="failed", error=f"{type(e).__name__}: {e}")
        print(f"[모델 서버] 적재 실패: {STATE['error']}", flush=True)


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=_load_models, daemon=True).start()
    yield


app = FastAPI(title="MOA 모델 추론 서버", lifespan=lifespan)


def check_token(x_model_token: str = Header(default=None)):
    if TOKEN and x_model_token != TOKEN:
        raise HTTPException(status_code=401, detail="토큰 불일치")


def require_ready():
    if STATE["status"] != "ready":
        raise HTTPException(status_code=503, detail=f"모델 준비 상태: {STATE['status']}")


def read_rgb(f: UploadFile):
    img = cv2.imdecode(np.frombuffer(f.file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail=f"이미지 해석 실패: {f.filename}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def read_mask(f: UploadFile, size):
    m = cv2.imdecode(np.frombuffer(f.file.read(), np.uint8), cv2.IMREAD_GRAYSCALE)
    if m is None:
        raise HTTPException(status_code=400, detail=f"마스크 해석 실패: {f.filename}")
    if (m.shape[1], m.shape[0]) != size:
        m = cv2.resize(m, size, interpolation=cv2.INTER_NEAREST)
    return (m > 127).astype(np.uint8)


def png(arr, rgb=True):
    ok, buf = cv2.imencode(".png", cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if rgb else arr)
    return buf.tobytes()


def parse_points(text):
    return [tuple(p) for p in json.loads(text)] if text else None


@app.get("/health")
def health():
    import torch

    gpu = None
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        gpu = {"name": torch.cuda.get_device_name(0), "vram_total_gb": round(total / 1024**3, 2),
               "vram_free_gb": round(free / 1024**3, 2)}
    composer = MODELS.get("composer")
    upscale = composer.upscale_ckpt if composer is not None else None
    return {**STATE, "weights": os.environ.get("ANYDOOR_CKPT"), "upscale": upscale, "save_memory": SAVE_MEMORY, "gpu": gpu}


@app.post("/extract", dependencies=[Depends(check_token), Depends(require_ready)])
def extract(image: UploadFile = File(...), points: str = Form(None), neg_points: str = Form(None),
            box: str = Form(None), image_key: str = Form(None)):
    rgb = read_rgb(image)
    t0 = time.time()
    with GPU_LOCK:
        try:
            mask = MODELS["sam2"].extract(rgb, points=parse_points(points), neg_points=parse_points(neg_points),
                                          box=tuple(json.loads(box)) if box else None, image_key=image_key)
        except ValueError as e:  # 점·상자 좌표 오류
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError:  # SAM2 결과 빈 마스크
            raise HTTPException(status_code=422, detail="EMPTY_MASK")
        finally:
            _release()
    return Response(png(mask.astype(np.uint8) * 255, rgb=False), media_type="image/png",
                    headers={"X-Elapsed-Sec": f"{time.time() - t0:.2f}"})


@app.post("/compose", dependencies=[Depends(check_token), Depends(require_ready)])
def compose(garment: UploadFile = File(...), garment_mask: UploadFile = File(...), person: UploadFile = File(...),
            area: UploadFile = File(...), seed: int = Form(None), steps: int = Form(50),
            shape_control: bool = Form(False), refine: bool = Form(False)):
    ref = read_rgb(garment)
    tar = read_rgb(person)
    ref_mask = read_mask(garment_mask, (ref.shape[1], ref.shape[0]))
    tar_mask = read_mask(area, (tar.shape[1], tar.shape[0]))
    if ref_mask.sum() == 0 or tar_mask.sum() == 0:
        raise HTTPException(status_code=400, detail="빈 마스크")
    composer = MODELS["composer"]
    t0 = time.time()
    with GPU_LOCK:
        try:
            PROGRESS["progress"] = 0.0
            result = composer.compose(ref, ref_mask, tar, tar_mask, seed=seed, steps=steps,
                                      shape_control=shape_control, refine=refine,
                                      on_progress=lambda v: PROGRESS.update(progress=round(min(v, 1.0), 3)))
            crop = composer.last_crop_box
        finally:
            PROGRESS["progress"] = None
            _release()
    return Response(png(result), media_type="image/png",
                    headers={"X-Crop-Box": ",".join(map(str, crop)), "X-Elapsed-Sec": f"{time.time() - t0:.2f}"})


@app.get("/progress", dependencies=[Depends(check_token)])
def progress():
    return PROGRESS
