# backend/main.py
# 웹/PyQt 클라이언트가 공통으로 쓰는 API 서버.
# 실행: uvicorn main:app --host 0.0.0.0 --port 8000
#
# 사용 흐름
#   1) POST /extract   : 원본 사진 + 클릭 좌표 -> SAM으로 객체만 추출 (빠름, 수초)
#                        결과를 서버에 저장하고 extraction_id + 미리보기 PNG 제공
#   2) (클라이언트)     : 미리보기를 배경 위에 드래그/리사이즈해서 배치 확정
#   3) POST /composite : extraction_id + 배경 + 배치영역 마스크 -> 큐에 등록 (AnyDoor, 수분)
#   4) GET  /job/{id}  : 진행 상태 폴링
#   5) GET  /result/{id}: 완성 이미지

import os
import json
import uuid
import random
import logging

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import init_db, get_session, SessionLocal, User, Extraction, CompositeJob
from auth import register_user, login_user, get_current_user, ensure_test_account
from pipeline import extract_mask_candidates, make_cutout_png
from queue_worker import enqueue_job, start_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("server.log", encoding="utf-8")],
)
logger = logging.getLogger("cgi.main")

app = FastAPI(title="CGI Composite API")

# 웹 클라이언트는 다른 포트(정적 서버)에서 이 API를 호출하므로 CORS 허용이 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 개발 편의용. 배포 시 실제 도메인으로 제한할 것
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE = "storage"
EXTRACT_DIR = os.path.join(STORAGE, "extractions")
UPLOAD_DIR = os.path.join(STORAGE, "uploads")
RESULT_DIR = os.path.join(STORAGE, "results")
for d in (EXTRACT_DIR, UPLOAD_DIR, RESULT_DIR):
    os.makedirs(d, exist_ok=True)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        ensure_test_account(db)
    finally:
        db.close()
    start_worker()
    logger.info(f"서버 시작 완료 (테스트 계정: test / test1234)")


def _decode_image(file_bytes: bytes) -> np.ndarray:
    """업로드된 바이트 -> RGB numpy 배열."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _save_bytes(data: bytes, path: str):
    with open(path, "wb") as f:
        f.write(data)


# ── 인증 ────────────────────────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/register")
def register(req: AuthRequest, db: Session = Depends(get_session)):
    user = register_user(db, req.username, req.password)
    logger.info(f"신규 가입: {user.username}")
    return {"id": user.id, "username": user.username}


@app.post("/auth/login")
def login(req: AuthRequest, db: Session = Depends(get_session)):
    token = login_user(db, req.username, req.password)
    logger.info(f"로그인: {req.username}")
    return {"token": token}


# ── 1단계: 객체 추출 (SAM만, 여기서 딱 한 번 실행) ────────────────────────
def _parse_points(points_json: str | None, point_x: int | None, point_y: int | None,
                   w: int, h: int) -> list[tuple[int, int, int]]:
    """
    클릭 점 목록을 파싱한다. 새 클라이언트는 points(JSON)를, 예전 클라이언트(PyQt)는
    point_x/point_y 하나만 보내므로 둘 다 받아준다.
    반환: [(x, y, label), ...]  label 1=더하기, 0=빼기
    """
    if points_json:
        try:
            raw = json.loads(points_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="points 형식이 올바르지 않습니다.")
        points = [(int(p["x"]), int(p["y"]), int(p.get("label", 1))) for p in raw]
    elif point_x is not None and point_y is not None:
        points = [(point_x, point_y, 1)]
    else:
        raise HTTPException(status_code=400, detail="클릭 지점이 없습니다.")

    if not points:
        raise HTTPException(status_code=400, detail="클릭 지점이 없습니다.")
    for x, y, _ in points:
        if not (0 <= x < w and 0 <= y < h):
            raise HTTPException(status_code=400, detail="클릭 좌표가 이미지 범위를 벗어났습니다.")
    if not any(label == 1 for _, _, label in points):
        raise HTTPException(status_code=400, detail="더하기 점이 최소 하나는 있어야 합니다.")
    return points


def _build_candidates(image_rgb, points, ext_id: str) -> tuple[list, list, list]:
    """점 목록으로 마스크 후보를 만들고 파일로 저장한다. (마스크경로, 컷아웃경로, 영역비율)"""
    h, w = image_rgb.shape[:2]
    candidates = extract_mask_candidates(image_rgb, points)
    if candidates[0]["area"] < 50:
        raise HTTPException(status_code=422, detail="객체를 인식하지 못했습니다. 다른 지점을 찍어보세요.")

    mask_paths, cutout_paths, coverages = [], [], []
    for i, cand in enumerate(candidates):
        mask = cand["mask"]
        # alpha 는 BiRefNet 이 다듬은 0~255 값(없으면 SAM 마스크를 0/255 로 변환한 것).
        # 합성 로직은 이진 마스크를 쓰고, 미리보기 컷아웃은 부드러운 알파를 써야
        # 털 가장자리가 자연스럽게 보인다.
        alpha = cand.get("alpha")
        if alpha is None:
            alpha = (mask * 255).astype(np.uint8)

        mask_path = os.path.join(EXTRACT_DIR, f"{ext_id}_mask_{i}.png")
        cutout_path = os.path.join(EXTRACT_DIR, f"{ext_id}_cutout_{i}.png")
        cv2.imwrite(mask_path, alpha)
        _save_bytes(make_cutout_png(image_rgb, alpha), cutout_path)
        mask_paths.append(mask_path)
        cutout_paths.append(cutout_path)
        coverages.append(round(cand["area"] / (h * w), 4))
    return mask_paths, cutout_paths, coverages


@app.post("/extract")
async def extract_endpoint(
    image: UploadFile = File(..., description="객체가 포함된 원본 사진"),
    points: str | None = Form(None, description='클릭 점 목록 JSON: [{"x":1,"y":2,"label":1}, ...]'),
    point_x: int | None = Form(None, description="(구버전 호환) 클릭 x 좌표"),
    point_y: int | None = Form(None, description="(구버전 호환) 클릭 y 좌표"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    raw = await image.read()
    image_rgb = _decode_image(raw)
    h, w = image_rgb.shape[:2]

    parsed_points = _parse_points(points, point_x, point_y, w, h)

    ext_id = str(uuid.uuid4())
    src_path = os.path.join(EXTRACT_DIR, f"{ext_id}_src.png")
    cv2.imwrite(src_path, cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))

    mask_paths, cutout_paths, coverages = _build_candidates(image_rgb, parsed_points, ext_id)

    db.add(Extraction(
        id=ext_id, user_id=user.id,
        src_image_path=src_path,
        candidate_masks=json.dumps(mask_paths),
        candidate_cutouts=json.dumps(cutout_paths),
        active_candidate=0,   # 기본값: 면적이 가장 큰 후보 (extract_mask_candidates가 이미 면적순 정렬)
        points=json.dumps([{"x": x, "y": y, "label": l} for x, y, l in parsed_points]),
    ))
    db.commit()

    logger.info(
        f"객체 추출 완료: {ext_id} (user={user.username}, 점 {len(parsed_points)}개, "
        f"후보 {len(coverages)}개, 기본 선택 영역비율={coverages[0]:.1%})"
    )

    return {"extraction_id": ext_id, "coverage": coverages[0],
            "candidate_count": len(coverages), "candidates": coverages}


class RefineRequest(BaseModel):
    points: list[dict]   # [{"x": .., "y": .., "label": 1|0}, ...]


@app.post("/extract/{extraction_id}/refine")
def refine_extraction(extraction_id: str, req: RefineRequest,
                       db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """
    점을 추가/삭제한 뒤 같은 추출 건을 다시 계산한다.
    이미지를 다시 업로드하지 않고 서버에 저장된 원본을 재사용하므로 빠르다.
    """
    ext = db.query(Extraction).filter(
        Extraction.id == extraction_id, Extraction.user_id == user.id
    ).first()
    if ext is None:
        raise HTTPException(status_code=404, detail="추출 결과를 찾을 수 없습니다.")

    bgr = cv2.imread(ext.src_image_path)
    if bgr is None:
        raise HTTPException(status_code=410, detail="원본 이미지가 사라졌습니다. 처음부터 다시 해주세요.")
    image_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]

    parsed_points = _parse_points(json.dumps(req.points), None, None, w, h)
    mask_paths, cutout_paths, coverages = _build_candidates(image_rgb, parsed_points, extraction_id)

    ext.candidate_masks = json.dumps(mask_paths)
    ext.candidate_cutouts = json.dumps(cutout_paths)
    ext.active_candidate = 0
    ext.points = json.dumps([{"x": x, "y": y, "label": l} for x, y, l in parsed_points])
    db.commit()

    logger.info(f"추출 갱신: {extraction_id} (점 {len(parsed_points)}개, 영역비율={coverages[0]:.1%})")
    return {"extraction_id": extraction_id, "coverage": coverages[0],
            "candidate_count": len(coverages), "candidates": coverages}


@app.get("/extract/{extraction_id}/cutout")
def get_cutout(extraction_id: str, db: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    """현재 채택된 후보의 투명배경 PNG. 클라이언트가 배경 위에 얹어 배치하는 데 쓴다."""
    ext = db.query(Extraction).filter(
        Extraction.id == extraction_id, Extraction.user_id == user.id
    ).first()
    if ext is None:
        raise HTTPException(status_code=404, detail="추출 결과를 찾을 수 없습니다.")
    return FileResponse(ext.cutout_path, media_type="image/png")


@app.get("/extract/{extraction_id}/candidate/{index}")
def get_candidate_cutout(extraction_id: str, index: int, db: Session = Depends(get_session),
                          user: User = Depends(get_current_user)):
    """다른 후보(index)의 투명배경 PNG 미리보기. '이거 아닌데' 싶을 때 대안을 보여주는 용도."""
    ext = db.query(Extraction).filter(
        Extraction.id == extraction_id, Extraction.user_id == user.id
    ).first()
    if ext is None:
        raise HTTPException(status_code=404, detail="추출 결과를 찾을 수 없습니다.")
    cutout_paths = json.loads(ext.candidate_cutouts)
    if not (0 <= index < len(cutout_paths)):
        raise HTTPException(status_code=404, detail="해당 후보가 없습니다.")
    return FileResponse(cutout_paths[index], media_type="image/png")


class SelectCandidateRequest(BaseModel):
    candidate: int


@app.post("/extract/{extraction_id}/select")
def select_candidate(extraction_id: str, req: SelectCandidateRequest,
                      db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """다른 후보로 채택을 바꾼다. 이후 /extract/{id}/cutout, /composite 는 이 후보를 쓴다."""
    ext = db.query(Extraction).filter(
        Extraction.id == extraction_id, Extraction.user_id == user.id
    ).first()
    if ext is None:
        raise HTTPException(status_code=404, detail="추출 결과를 찾을 수 없습니다.")
    candidate_count = len(json.loads(ext.candidate_cutouts))
    if not (0 <= req.candidate < candidate_count):
        raise HTTPException(status_code=400, detail="해당 후보가 없습니다.")
    ext.active_candidate = req.candidate
    db.commit()
    logger.info(f"후보 변경: {extraction_id} -> candidate {req.candidate} (user={user.username})")
    return {"extraction_id": extraction_id, "active_candidate": req.candidate}


# ── 2단계: 합성 요청 (큐에 등록만 하고 즉시 응답) ─────────────────────────
@app.post("/composite")
async def composite_endpoint(
    extraction_id: str = Form(..., description="/extract 로 만든 추출 결과 id"),
    bg_image: UploadFile = File(..., description="객체를 넣을 배경 사진"),
    placement_mask: UploadFile = File(..., description="드래그/리사이즈로 확정한 배치 영역(흑백)"),
    client_type: str = Form("web"),
    guidance_scale: float = Form(5.0),
    seed: int = Form(-1, description="결과 재현용 시드. -1이면 무작위로 하나 뽑아 기록한다."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    ext = db.query(Extraction).filter(
        Extraction.id == extraction_id, Extraction.user_id == user.id
    ).first()
    if ext is None:
        raise HTTPException(status_code=404, detail="추출 결과를 찾을 수 없습니다. 객체 추출부터 다시 해주세요.")

    # 시드를 -1로 보내면 여기서 하나 뽑아 DB에 기록한다.
    # 그래야 나중에 "그때 그 결과"를 똑같이 다시 만들 수 있다.
    if seed is None or seed < 0:
        seed = random.randint(0, 2**31 - 1)

    job_uid = str(uuid.uuid4())
    bg_path = os.path.join(UPLOAD_DIR, f"{job_uid}_bg.png")
    mask_path = os.path.join(UPLOAD_DIR, f"{job_uid}_placement.png")
    result_path = os.path.join(RESULT_DIR, f"{job_uid}_result.png")

    _save_bytes(await bg_image.read(), bg_path)
    _save_bytes(await placement_mask.read(), mask_path)

    job = CompositeJob(
        user_id=user.id,
        client_type=client_type,
        extraction_id=ext.id,
        ref_image_path=ext.src_image_path,
        ref_mask_path=ext.mask_path,
        bg_image_path=bg_path,
        placement_mask_path=mask_path,
        result_image_path=result_path,
        status="queued",
        guidance_scale=int(guidance_scale),
        seed=seed,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    enqueue_job(job.id)
    logger.info(f"합성 접수: job #{job.id} (user={user.username}, client={client_type}, seed={seed})")

    return {"job_id": job.id, "status": "queued", "seed": seed}


# ── 상태 폴링 / 결과 / 기록 ───────────────────────────────────────────────
@app.get("/job/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    job = db.query(CompositeJob).filter(
        CompositeJob.id == job_id, CompositeJob.user_id == user.id
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return {
        "id": job.id,
        "status": job.status,
        "error_message": job.error_message,
        "seed": job.seed,
    }


@app.get("/result/{job_id}")
def get_result(job_id: int, db: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    job = db.query(CompositeJob).filter(
        CompositeJob.id == job_id, CompositeJob.user_id == user.id
    ).first()
    if job is None or job.status != "done":
        raise HTTPException(status_code=404, detail="결과 없음 또는 아직 처리 중")
    return FileResponse(job.result_image_path, media_type="image/png")


@app.get("/history")
def get_history(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """로그인 계정 기준 작업 기록. PyQt에서 만든 작업이 웹에서도 보이는 동기화 지점."""
    jobs = (
        db.query(CompositeJob)
        .filter(CompositeJob.user_id == user.id)
        .order_by(CompositeJob.created_at.desc())
        .all()
    )
    return [
        {
            "id": j.id,
            "client_type": j.client_type,
            "status": j.status,
            "seed": j.seed,
            "guidance_scale": j.guidance_scale,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]


@app.get("/health")
def health():
    return {"status": "ok"}
