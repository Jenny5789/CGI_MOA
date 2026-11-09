"""옛 사진 기록(storage/images/img_*.json)을 DB images 표로 한 번 옮긴다.

사진 정보를 DB에서만 읽게 바꾼 뒤(11/2), 그 전에 올린 사진은 DB에 행이 없어 추출·합성·"재료 보기"에서 찾지 못한다. 그 행을 채운다.

- 기본은 확인만 한다 (DB에 쓰지 않음). 실제로 넣으려면 --apply
- 이미 DB에 있는 사진은 건너뛴다. 사진 파일이 없거나 올린 회원이 DB에 없는 기록은 넣지 않고 번호를 알려 준다
- json은 지우지 않는다. 여러 번 실행해도 같은 결과다
- 옛 기록에 없는 칸: thumb은 파일이 있으면 채우고, content_hash는 저장된 사진 파일의 SHA-256, from_sample은 아니오로 넣는다
  (옛 기록은 24시간이 지나 최근 사용한 사진 목록에 나오지 않으므로 이 값은 영향이 없다)
- 시각은 json의 한국 시간을 DB 방식(UTC, 시간대 없음)으로 바꿔 넣는다

예 (저장소 맨 위 폴더에서, CGI 환경):
    CGI\\Scripts\\python.exe scripts\\import_image_json.py
    CGI\\Scripts\\python.exe scripts\\import_image_json.py --apply
"""
import hashlib
import json

from _import_common import parse_args, report, to_utc  # 저장소 맨 위 폴더를 import 경로에 넣는 일도 여기서 한다 (backend 패키지를 쓰려고)

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.config import IMAGE_KINDS, IMAGES_DIR
from backend.db import DATABASE_URL, UploadedImage, User


def main():
    args = parse_args("옛 사진 기록(json)을 DB images 표로 옮기기", "--images-dir", IMAGES_DIR, "사진 json이 있는 폴더 (기본 storage/images)")

    skipped = {"이미 DB에 있음": [], "읽을 수 없는 기록": [], "사진 파일 없음": [], "올린 회원이 DB에 없음": []}
    rows = []
    with sessionmaker(create_engine(DATABASE_URL))() as s:
        users = set(s.scalars(select(User.id)))
        have = set(s.scalars(select(UploadedImage.image_id)))
        for path in sorted(args.src_dir.glob("img_*.json")):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
                image_id, user_id, filename, kind = rec["image_id"], rec["user_id"], rec["filename"], rec["kind"]
                width, height = int(rec["width"]), int(rec["height"])
                created = to_utc(rec["created_at"])
                if kind not in IMAGE_KINDS:
                    raise ValueError(kind)
            except (OSError, ValueError, KeyError, TypeError):
                skipped["읽을 수 없는 기록"].append(path.name)
                continue
            if image_id in have:
                skipped["이미 DB에 있음"].append(image_id)
            elif not (args.src_dir / filename).is_file():
                skipped["사진 파일 없음"].append(image_id)
            elif user_id not in users:
                skipped["올린 회원이 DB에 없음"].append(image_id)
            else:
                thumb = f"{image_id}_thumb.jpg"
                rows.append(UploadedImage(
                    image_id=image_id, user_id=user_id, kind=kind, filename=filename,
                    thumb=thumb if (args.src_dir / thumb).is_file() else None, width=width, height=height,
                    content_hash=hashlib.sha256((args.src_dir / filename).read_bytes()).hexdigest(),
                    from_sample=False, created_at=created,
                ))
        if args.apply and rows:
            s.add_all(rows)
            s.commit()

    report(args.apply, len(rows), skipped)


if __name__ == "__main__":
    main()
