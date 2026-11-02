"""옛 합성 결과 기록(storage/results/res_*.json)을 DB results 표로 한 번 옮긴다.

합성 결과 정보를 DB에서만 읽게 바꾼 뒤(11/2), 그 전에 만든 결과는 DB에 행이 없어 사진첩·내 작업 기록에 나오지 않는다. 그 행을 채운다.
먼저 scripts/import_image_json.py, import_extraction_json.py, import_job_json.py 로 사진·추출 결과·작업 기록을 옮겨야 한다.

- 기본은 확인만 한다 (DB에 쓰지 않음). 실제로 넣으려면 --apply
- 사진첩 정보(saved 저장, favorite 좋아요)는 그대로 옮긴다
- 이미 DB에 있는 기록은 건너뛴다. 결과 사진(큰 사진·작은 사진) 파일이 없거나, 회원·두 사진(상의 사진, 인물 사진)이 DB에 없는 기록은 넣지 않고 번호를 알려 준다
- 연결된 작업·추출 결과가 DB에 없으면 그 연결만 비워서 넣는다 (저장한 결과를 버리지 않기 위해, 이 경우 "재료 보기"만 안 됨). 따로 알려 준다
- json과 사진 파일은 지우지 않는다. 여러 번 실행해도 같은 결과다
- 분석용 값 (seam_fix, crop_box, restore_original, garment_found)은 옛 기록에 있는 것만 detail 칸(JSON)에 넣는다
- 시각은 json의 한국 시간을 DB 방식(UTC, 시간대 없음)으로 바꿔 넣는다

예 (저장소 맨 위 폴더에서, CGI 환경):
    CGI\\Scripts\\python.exe scripts\\import_result_json.py
    CGI\\Scripts\\python.exe scripts\\import_result_json.py --apply
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.config import RESULTS_DIR  # noqa: E402
from backend.db import DATABASE_URL, Extraction, Job, Result, UploadedImage, User  # noqa: E402

DETAIL_KEYS = ("seam_fix", "crop_box", "restore_original", "garment_found")


def to_utc(text):
    return datetime.fromisoformat(text).astimezone(timezone.utc).replace(tzinfo=None)


def main():
    parser = argparse.ArgumentParser(description="옛 합성 결과 기록(json)을 DB results 표로 옮기기")
    parser.add_argument("--apply", action="store_true", help="실제로 DB에 넣는다 (없으면 확인만)")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR, help="결과 json과 사진이 있는 폴더 (기본 storage/results)")
    args = parser.parse_args()
    if not DATABASE_URL:
        sys.exit("DATABASE_URL이 없습니다 (backend/.env). 설정: docs/database.md")

    engine = create_engine(DATABASE_URL)
    skipped = {"이미 DB에 있음": [], "읽을 수 없는 기록": [], "결과 사진 파일 없음": [], "회원이 DB에 없음": [], "상의·인물 사진이 DB에 없음": []}
    unlinked = {"작업 연결 비움": [], "추출 결과 연결 비움": []}
    rows = []
    with sessionmaker(engine)() as s:
        users = set(s.scalars(select(User.id)))
        images = set(s.scalars(select(UploadedImage.image_id)))
        extractions = set(s.scalars(select(Extraction.extraction_id)))
        jobs = set(s.scalars(select(Job.job_id)))
        have = set(s.scalars(select(Result.result_id))) if inspect(engine).has_table(Result.__tablename__) else set()
        for path in sorted(args.results_dir.glob("res_*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
                result_id, user_id = rec["result_id"], rec["user_id"]
                garment_id, person_id = rec["garment_image_id"], rec["person_image_id"]
                values = dict(
                    result_id=result_id, user_id=user_id, garment_image_id=garment_id, person_image_id=person_id,
                    saved=bool(rec.get("saved", False)), favorite=bool(rec.get("favorite", False)),
                    seed=int(rec["seed"]) if rec.get("seed") is not None else None,
                    detail={k: rec[k] for k in DETAIL_KEYS if k in rec}, created_at=to_utc(rec["created_at"]),
                )
            except (OSError, ValueError, KeyError, TypeError):
                skipped["읽을 수 없는 기록"].append(path.name)
                continue
            if result_id in have:
                skipped["이미 DB에 있음"].append(result_id)
            elif not all((args.results_dir / name).is_file() for name in (f"{result_id}.png", f"{result_id}_thumb.jpg")):
                skipped["결과 사진 파일 없음"].append(result_id)
            elif user_id not in users:
                skipped["회원이 DB에 없음"].append(result_id)
            elif garment_id not in images or person_id not in images:
                skipped["상의·인물 사진이 DB에 없음"].append(result_id)
            else:
                job_id, extraction_id = rec.get("job_id"), rec.get("extraction_id")
                values["job_id"] = job_id if job_id in jobs else None
                values["extraction_id"] = extraction_id if extraction_id in extractions else None
                if values["job_id"] is None:
                    unlinked["작업 연결 비움"].append(result_id)
                if values["extraction_id"] is None:
                    unlinked["추출 결과 연결 비움"].append(result_id)
                rows.append(Result(**values))
        saved_count = sum(1 for r in rows if r.saved)  # 저장(commit)하면 객체 값이 만료되므로 미리 센다
        favorite_count = sum(1 for r in rows if r.favorite)
        if args.apply and rows:
            Result.__table__.create(engine, checkfirst=True)  # 표가 아직 없으면 만든다 (서버가 켜질 때 만드는 것과 같음)
            s.add_all(rows)
            s.commit()

    print(f"{'넣음' if args.apply else '넣을 예정 (확인만, DB에 쓰지 않음)'}: {len(rows)}개 (사진첩에 저장한 것 {saved_count}개, 좋아요 {favorite_count}개)")
    for reason, ids in {**skipped, **unlinked}.items():
        print(f"{'건너뜀' if reason in skipped else '넣되'} - {reason}: {len(ids)}개" + (f" {ids}" if ids and reason != "이미 DB에 있음" else ""))
    if not args.apply and rows:
        print("실제로 넣으려면 --apply 를 붙여 다시 실행하세요.")


if __name__ == "__main__":
    main()
