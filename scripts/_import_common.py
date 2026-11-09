"""옛 json 기록을 DB로 옮기는 스크립트 4개(import_*_json.py)가 함께 쓰는 부분. 11/2 DB 이전용이고, 사용법은 docs/database.md 6장.

- 이 파일을 가져오면 저장소 맨 위 폴더가 import 경로에 들어가 backend 패키지를 쓸 수 있다 (스크립트에서 backend보다 먼저 가져올 것)
- to_utc: json의 한국 시간 글자를 DB 방식(UTC, 시간대 없음)으로 바꾼다
- parse_args: --apply와 json 폴더 옵션을 받고, DATABASE_URL이 없으면 알리고 끝낸다
- report: 넣은 개수와 건너뛴 기록을 같은 모양으로 알린다
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import DATABASE_URL  # noqa: E402


def to_utc(text):
    return datetime.fromisoformat(text).astimezone(timezone.utc).replace(tzinfo=None)


def parse_args(description, dir_option, default_dir, dir_help):
    """--apply(실제로 넣기)와 json 폴더 옵션(dir_option, 예: --images-dir)을 받는다. 폴더는 args.src_dir로 읽는다"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--apply", action="store_true", help="실제로 DB에 넣는다 (없으면 확인만)")
    parser.add_argument(dir_option, dest="src_dir", type=Path, default=default_dir, help=dir_help)
    args = parser.parse_args()
    if not DATABASE_URL:
        sys.exit("DATABASE_URL이 없습니다 (backend/.env). 설정: docs/database.md")
    return args


def report(apply, count, skipped, count_note="", unlinked=None):
    """결과를 알린다. skipped: {이유: [번호, ...]} 넣지 않은 기록, unlinked: {이유: [번호, ...]} 넣되 연결만 비운 기록 (결과 이전만 씀)"""
    print(f"{'넣음' if apply else '넣을 예정 (확인만, DB에 쓰지 않음)'}: {count}개{count_note}")
    for reason, ids in {**skipped, **(unlinked or {})}.items():
        print(f"{'건너뜀' if reason in skipped else '넣되'} - {reason}: {len(ids)}개" + (f" {ids}" if ids and reason != "이미 DB에 있음" else ""))
    if not apply and count:
        print("실제로 넣으려면 --apply 를 붙여 다시 실행하세요.")
