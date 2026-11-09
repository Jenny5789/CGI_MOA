"""옛 추출 기록(storage/extractions/ext_*.json)을 DB extractions 표로 한 번 옮긴다.

추출 결과 정보를 DB에서만 읽게 바꾼 뒤(11/2), 그 전에 추출한 기록은 DB에 행이 없어 합성·"재료 보기"에서 찾지 못한다. 그 행을 채운다.
먼저 scripts/import_image_json.py 로 사진 기록을 옮겨야 한다 (추출 기록은 사진 행을 가리킨다).

- 기본은 확인만 한다 (DB에 쓰지 않음). 실제로 넣으려면 --apply
- 이미 DB에 있는 기록은 건너뛴다. 추출한 사진이 DB에 없거나, 올린 회원이 없거나, 윤곽·cutout 파일이 없는 기록은 넣지 않고 번호를 알려 준다
- json은 지우지 않는다. 여러 번 실행해도 같은 결과다
- box 칸이 없는 옛 기록(박스 선택 이전)은 box를 비워 둔다. points, box, bbox는 detail 칸(JSON)에 넣는다
- 시각은 json의 한국 시간을 DB 방식(UTC, 시간대 없음)으로 바꿔 넣는다

예 (저장소 맨 위 폴더에서, CGI 환경):
    CGI\\Scripts\\python.exe scripts\\import_extraction_json.py
    CGI\\Scripts\\python.exe scripts\\import_extraction_json.py --apply
"""
import json

from _import_common import parse_args, report, to_utc  # 저장소 맨 위 폴더를 import 경로에 넣는 일도 여기서 한다 (backend 패키지를 쓰려고)

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from backend.config import EXTRACTIONS_DIR
from backend.db import DATABASE_URL, Extraction, UploadedImage, User


def main():
    args = parse_args("옛 추출 기록(json)을 DB extractions 표로 옮기기", "--extractions-dir", EXTRACTIONS_DIR, "추출 json이 있는 폴더 (기본 storage/extractions)")

    engine = create_engine(DATABASE_URL)
    skipped = {"이미 DB에 있음": [], "읽을 수 없는 기록": [], "윤곽·cutout 파일 없음": [], "추출한 사진이 DB에 없음": [],
               "올린 회원이 DB에 없음": []}
    rows = []
    with sessionmaker(engine)() as s:
        users = set(s.scalars(select(User.id)))
        images = set(s.scalars(select(UploadedImage.image_id)))
        have = set(s.scalars(select(Extraction.extraction_id))) if inspect(engine).has_table(Extraction.__tablename__) else set()
        for path in sorted(args.src_dir.glob("ext_*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
                extraction_id, user_id, image_id = rec["extraction_id"], rec["user_id"], rec["image_id"]
                width, height, mask, cutout = int(rec["width"]), int(rec["height"]), rec["mask"], rec["cutout"]
                seconds = float(rec["seconds"])
                detail = {"points": rec["points"], "box": rec.get("box"), "bbox": rec["bbox"]}
                created = to_utc(rec["created_at"])
            except (OSError, ValueError, KeyError, TypeError):
                skipped["읽을 수 없는 기록"].append(path.name)
                continue
            if extraction_id in have:
                skipped["이미 DB에 있음"].append(extraction_id)
            elif not (args.src_dir / mask).is_file() or not (args.src_dir / cutout).is_file():
                skipped["윤곽·cutout 파일 없음"].append(extraction_id)
            elif image_id not in images:
                skipped["추출한 사진이 DB에 없음"].append(extraction_id)
            elif user_id not in users:
                skipped["올린 회원이 DB에 없음"].append(extraction_id)
            else:
                rows.append(Extraction(extraction_id=extraction_id, user_id=user_id, image_id=image_id, width=width, height=height,
                                       mask=mask, cutout=cutout, seconds=seconds, detail=detail, created_at=created))
        if args.apply and rows:
            Extraction.__table__.create(engine, checkfirst=True)  # 표가 아직 없으면 만든다 (서버가 켜질 때 만드는 것과 같음)
            s.add_all(rows)
            s.commit()

    report(args.apply, len(rows), skipped)


if __name__ == "__main__":
    main()
