# MOA 서버 (FastAPI)

- 역할: 화면(frontend) 요청 수신 → AI 기능(SAM2 추출, 합성) 실행 → 결과 반환
- 기준 문서: 팀 API 명세 [../docs/api.md](../docs/api.md)

## 실행

- 실행 위치: 저장소 맨 위 폴더
- 실행 환경: `CGI` 가상환경 (SAM2·AnyDoor 설치 환경, 다른 환경에서는 AI 기능 호출 불가)
- 실행 명령: `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 종료: 실행 창에서 Ctrl+C

## 동작 확인

- http://localhost:8000/api/health → `{"status":"ok"}`
- http://localhost:8000/docs → 주소 목록·시험 화면 (FastAPI 자동 생성)

## 파일별 담당

- 2026-10-14부터 서버 전체를 AI 기능 담당이 맡음 (서버 담당 = AI 기능 담당)

| 파일 | 명세 | 내용 | 상태 |
|---|---|---|---|
| `main.py` | - | 서버 시작, 주소 연결, `/api/health`, AnyDoor 예열 | 완료 |
| `routers/images.py` | 3-1 | 사진 올리기 (파일 저장) | 완료 |
| `routers/files.py` | 7장 | 파일 보기 (보호 없음) | 완료 |
| `errors.py`, `config.py` | 0장 | 오류 형식, 저장 위치·제한 값 | 완료 |
| `routers/extract.py` | 4-1 | SAM2 상의 추출 (점, 박스) | 완료 |
| `storage.py`, `gpu.py` | - | 저장 기록 찾기, GPU 한 번에 하나씩 사용 | 완료 |
| `routers/compose.py` | 5-1~5-2 | 합성 요청, 진행 확인 | 완료 |
| `routers/results.py` | 5-3, 6-1~6-2 | 결과 받기, 결과 목록, 저장/좋아요, 저장 안 한 결과 3일 삭제 | 완료 (10/14) |
| `routers/auth.py`, `auth.py`, `db.py` | 2-1~2-4 | 로그인, 회원가입, 내 정보, 로그아웃 (MySQL, [../docs/database.md](../docs/database.md)) | 완료 (10/15) |

## 임시 결정 사항

- 로그인: 시험 회원 `test` / `test1234` (서버가 켜질 때 자동 생성). 토큰 유효 3시간(10/15 결정, 로그인한 시각부터), DB에는 토큰 해시만 저장
- `backend/.env`가 없거나 MySQL에 연결 못 해도 서버는 켜짐 → 로그인 관련 주소만 503 `DB_UNAVAILABLE`
- 회원가입: 아이디 공백 없이 50자 이하, `name` 비우면 아이디로, `email` 선택. `/api/me`의 `avatar_url`은 `null` (프로필 사진 기능 없음)
- 사진·추출·합성·결과 주소는 아직 로그인 확인 없음 (명세상 "로그인 필요") → 다음 단계에서 붙이고 결과를 사람별로 나눔
- 사진·결과 기록은 DB 없이 파일로 저장 (`storage/images/` 올린 사진, `storage/extractions/` 추출 결과, `storage/jobs/` 합성 작업, `storage/results/` 합성 결과, 저장소 제외)
- 합성 작업 상태는 서버 메모리에 보관 → 서버 재시작 시 진행 중이던 작업은 실패(`SERVER_RESTARTED`)로 표시
- 파일 보기(`/api/files`) 보호 없음 → 누구나 열람 가능. 보호 방식은 명세 7장 미정

## 명세 외 추가 (제안, 팀 합의 필요)

- 로그인 시간 연장 (2026-10-15): 로그인·회원가입 응답에 `expires_at`, `POST /api/auth/extend`. 만료 30분 전 확인 / 10분 전 재확인은 화면 몫 → [../docs/login_extend.md](../docs/login_extend.md)

- 상의 추출(`/api/extract`)에 `box` 선택 값 추가 (2026-10-13): `{ x1, y1, x2, y2 }` 0~1 비율. 점만 / 박스만 / 박스 + 점 가능. 기존 점만 요청은 그대로 동작
