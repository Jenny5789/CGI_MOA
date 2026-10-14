# MOA 서버 (FastAPI)

- 명세: [../docs/api.md](../docs/api.md)

## 실행

- 위치: 저장소 맨 위 폴더, `CGI` 가상환경
- 명령: `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000` (종료 Ctrl+C)
- 확인: http://localhost:8000/api/health, 시험 화면 http://localhost:8000/docs

## 파일

| 파일 | 명세 | 내용 |
|---|---|---|
| `main.py` | - | 서버 시작, 주소 연결, AnyDoor 예열 |
| `config.py`, `errors.py` | 0장 | 저장 위치·제한 값, 오류 형식 |
| `db.py`, `auth.py`, `routers/auth.py` | 2장 | 로그인, 회원가입, 내 정보, 로그아웃, 연장 (MySQL) |
| `routers/images.py` | 3-1 | 사진 올리기 |
| `routers/extract.py` | 4-1 | SAM2 상의 추출 |
| `routers/compose.py` | 5-1~5-2 | 합성 요청, 진행 확인 |
| `routers/results.py` | 5-3, 6장 | 결과, 사진첩, 저장/좋아요 |
| `routers/files.py` | 7장 | 파일 보기 |
| `storage.py`, `gpu.py` | - | 기록 읽기·주인 확인, GPU 순서 |

## 임시 결정

- 시험 회원 `test` / `test1234` (서버 켤 때 자동 생성)
- 토큰 유효 3시간 (로그인 시각부터), DB에는 토큰 해시만 저장
- MySQL 연결 실패 시 로그인 주소만 503 `DB_UNAVAILABLE`
- 회원가입: 아이디 공백 없이 50자 이하, `name` 비우면 아이디, `email` 선택 / `avatar_url`은 `null`
- 모든 주소 로그인 필요 (`/api/files` 제외), 남의 기록은 404
- 사진·결과 기록은 `storage/`에 파일로 저장 (DB 아님)
- 합성 작업 상태는 메모리 보관 → 서버 재시작 시 진행 중 작업은 `SERVER_RESTARTED`
- `/api/files` 보호 없음 → 방식은 명세 7장에서 결정

## 명세 외 추가 (팀 합의 필요)

- 로그인 시간 연장: 응답에 `expires_at`, `POST /api/auth/extend` → [../docs/login_extend.md](../docs/login_extend.md)
- 상의 추출 `box`: `{ x1, y1, x2, y2 }` 0~1 비율, 점만 / 박스만 / 박스 + 점
