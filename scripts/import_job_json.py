"""옛 합성 작업 기록(storage/jobs/job_*.json)을 DB jobs 표로 한 번 옮긴다.

합성 작업 기록을 DB에서만 읽게 바꾼 뒤(11/2), 그 전에 만든 작업은 DB에 행이 없어 "재료 보기"에서 찾지 못한다. 그 행을 채운다.
먼저 scripts/import_image_json.py, scripts/import_extraction_json.py 로 사진·추출 결과 기록을 옮겨야 한다 (작업 기록은 둘을 가리킨다).

- 기본은 확인만 한다 (DB에 쓰지 않음). 실제로 넣으려면 --apply
- 이미 DB에 있는 기록은 건너뛴다. 입힐 영역·다듬은 윤곽 그림 파일이 없거나, 추출 결과·인물 사진·회원이 DB에 없는 기록은 넣지 않고 번호를 알려 준다
- json과 그림 파일은 지우지 않는다. 여러 번 실행해도 같은 결과다
- refine, shape_control, garment_mask 칸이 없는 옛 기록(합성 설정 이전)은 꺼짐·없음으로 넣는다
- 시각은 json의 한국 시간을 DB 방식(UTC, 시간대 없음)으로 바꿔 넣는다

예 (저장소 맨 위 폴더에서, CGI 환경):
    CGI\\Scripts\\python.exe scripts\\import_job_json.py
    CGI\\Scripts\\python.exe scripts\\import_job_json.py --apply
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.config import JOBS_DIR  # noqa: E402
from backend.db import DATABASE_URL, Extraction, Job, UploadedImage, User  # noqa: E402


def to_utc(text):
    return datetime.fromisoformat(text).astimezone(timezone.utc).replace(tzinfo=None)


def main():
    parser = argparse.ArgumentParser(description="옛 합성 작업 기록(json)을 DB jobs 표로 옮기기")
    parser.add_argument("--apply", action="store_true", help="실제로 DB에 넣는다 (없으면 확인만)")
    parser.add_argument("--jobs-dir", type=Path, default=JOBS_DIR, help="작업 json과 그림이 있는 폴더 (기본 storage/jobs)")
    args = parser.parse_args()
    if not DATABASE_URL:
        sys.exit("DATABASE_URL이 없습니다 (backend/.env). 설정: docs/database.md")

    engine = create_engine(DATABASE_URL)
    skipped = {"이미 DB에 있음": [], "읽을 수 없는 기록": [], "그림 파일 없음": [], "추출 결과가 DB에 없음": [],
               "인물 사진이 DB에 없음": [], "회원이 DB에 없음": []}
    rows = []
    with sessionmaker(engine)() as s:
        users = set(s.scalars(select(User.id)))
        images = set(s.scalars(select(UploadedImage.image_id)))
        extractions = set(s.scalars(select(Extraction.extraction_id)))
        have = set(s.scalars(select(Job.job_id))) if inspect(engine).has_table(Job.__tablename__) else set()
        for path in sorted(args.jobs_dir.glob("job_*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
                job_id, user_id, extraction_id, person_image_id = rec["job_id"], rec["user_id"], rec["extraction_id"], rec["person_image_id"]
                values = dict(
                    job_id=job_id, user_id=user_id, extraction_id=extraction_id, person_image_id=person_image_id,
                    status=rec["status"], progress=float(rec["progress"]), result_id=rec.get("result_id"), error=rec.get("error"),
                    area_mask=rec["area_mask"], garment_mask=rec.get("garment_mask"), refine=bool(rec.get("refine", False)),
                    shape_control=bool(rec.get("shape_control", False)), seed=int(rec["seed"]), created_at=to_utc(rec["created_at"]),
                    started_at=to_utc(rec["started_at"]) if rec.get("started_at") else None,
                    finished_at=to_utc(rec["finished_at"]) if rec.get("finished_at") else None,
                )
            except (OSError, ValueError, KeyError, TypeError):
                skipped["읽을 수 없는 기록"].append(path.name)
                continue
            files = [values["area_mask"]] + ([values["garment_mask"]] if values["garment_mask"] else [])
            if job_id in have:
                skipped["이미 DB에 있음"].append(job_id)
            elif not all((args.jobs_dir / name).is_file() for name in files):
                skipped["그림 파일 없음"].append(job_id)
            elif extraction_id not in extractions:
                skipped["추출 결과가 DB에 없음"].append(job_id)
            elif person_image_id not in images:
                skipped["인물 사진이 DB에 없음"].append(job_id)
            elif user_id not in users:
                skipped["회원이 DB에 없음"].append(job_id)
            else:
                rows.append(Job(**values))
        if args.apply and rows:
            Job.__table__.create(engine, checkfirst=True)  # 표가 아직 없으면 만든다 (서버가 켜질 때 만드는 것과 같음)
            s.add_all(rows)
            s.commit()

    print(f"{'넣음' if args.apply else '넣을 예정 (확인만, DB에 쓰지 않음)'}: {len(rows)}개")
    for reason, ids in skipped.items():
        print(f"건너뜀 - {reason}: {len(ids)}개" + (f" {ids}" if ids and reason != "이미 DB에 있음" else ""))
    if not args.apply and rows:
        print("실제로 넣으려면 --apply 를 붙여 다시 실행하세요.")


if __name__ == "__main__":
    main()
