# backend/queue_worker.py
# GPU 하나로 여러 사용자의 요청을 순서대로 처리하기 위한 작업 큐.
# 지금 규모(사내 소수 인원)엔 Redis/Celery 같은 별도 인프라 없이
# 파이썬 표준 큐 + 백그라운드 스레드로 충분하다.
# 트래픽이 커지면 이 파일만 Celery+Redis로 교체하면 되도록 인터페이스를 단순하게 유지.

import queue
import threading
import logging
from datetime import datetime

import cv2

from db import SessionLocal, CompositeJob
from pipeline import composite_with_synthetic_shadow

logger = logging.getLogger("cgi.queue")

job_queue: "queue.Queue[int]" = queue.Queue()


def enqueue_job(job_id: int):
    """API 핸들러가 새 작업을 큐에 등록할 때 호출."""
    job_queue.put(job_id)
    logger.info(f"[queue] job #{job_id} 등록됨 (대기열 길이: {job_queue.qsize()})")


def _process(job: CompositeJob):
    """
    실제 합성 1건. SAM은 이미 추출 단계에서 끝났으므로 여기서는 색감 보정 + 합성 +
    접지 그림자만 한다 (2026-09-21부터: composite() 단독 대신 그림자 포함 버전 사용.
    검증 내역은 트러블슈팅/2026-09-21_그림자실험/기록.md 참고).

    guidance_scale/seed는 예전 AnyDoor 전체재생성 방식의 흔적으로, 지금 합성 경로는
    결정론적이라 실제로 쓰지 않는다. DB 스키마 호환을 위해 컬럼만 남아있다.
    """
    ref_rgb = cv2.cvtColor(cv2.imread(job.ref_image_path), cv2.COLOR_BGR2RGB)
    ref_mask = (cv2.imread(job.ref_mask_path, cv2.IMREAD_GRAYSCALE) > 128).astype("uint8")

    bg_rgb = cv2.cvtColor(cv2.imread(job.bg_image_path), cv2.COLOR_BGR2RGB)
    placement_mask = (cv2.imread(job.placement_mask_path, cv2.IMREAD_GRAYSCALE) > 128).astype("uint8")

    result_rgb = composite_with_synthetic_shadow(
        ref_rgb, ref_mask,
        bg_rgb, placement_mask,
        method="auto",
    )
    cv2.imwrite(job.result_image_path, cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR))


def _worker_loop():
    """서버 시작 시 백그라운드 스레드로 계속 돌아가며 큐에서 하나씩 꺼내 처리."""
    while True:
        job_id = job_queue.get()          # 큐가 비어있으면 여기서 대기(블로킹)
        db = SessionLocal()
        job = None
        try:
            job = db.query(CompositeJob).filter(CompositeJob.id == job_id).first()
            if job is None:
                continue

            job.status = "processing"
            job.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"[queue] job #{job_id} 처리 시작")

            _process(job)

            job.status = "done"
            job.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"[queue] job #{job_id} 완료")

        except Exception as e:
            logger.exception(f"[queue] job #{job_id} 실패: {e}")
            if job is not None:
                try:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    job.updated_at = datetime.utcnow()
                    db.commit()
                except Exception:
                    db.rollback()
        finally:
            db.close()
            job_queue.task_done()


def start_worker():
    """FastAPI 서버 시작 시 한 번 호출. 데몬 스레드라 서버 종료 시 같이 정리됨."""
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()
    logger.info("[queue] 워커 스레드 시작됨")
