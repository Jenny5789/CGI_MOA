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

- 서버 담당자 부재 → AI 기능 담당이 틀 구축, AI 기능 부분 우선 작성
- 나머지는 빈칸 표시 후 서버 담당자에게 인계

| 파일 | 명세 | 내용 | 담당 | 상태 |
|---|---|---|---|---|
| `main.py` | - | 서버 시작, 주소 연결, `/api/health` | AI 기능 담당 (임시) | 완료 |
| `routers/images.py` | 3-1 | 사진 올리기 | AI 기능 담당 (임시, 파일 저장만) | 완료 |
| `routers/files.py` | 7장 | 파일 보기 | AI 기능 담당 (임시, 보호 없음) | 완료 |
| `errors.py`, `config.py` | 0장 | 오류 형식, 저장 위치·제한 값 | AI 기능 담당 (임시) | 완료 |
| `routers/extract.py` | 4-1 | SAM2 상의 추출 | AI 기능 담당 | 완료 |
| `storage.py`, `gpu.py` | - | 저장 기록 찾기, GPU 한 번에 하나씩 사용 | AI 기능 담당 (임시) | 완료 |
| `routers/compose.py` | 5-1~5-3 | 합성 요청, 진행 확인, 결과 | AI 기능 담당 | 완료 |
| `routers/auth.py` | 2-1~2-4 | 로그인, 회원가입, 내 정보 | 서버 담당자 | 미작성 |
| `routers/results.py` | 6-1~6-3 | 결과 목록, 저장/좋아요 | 서버 담당자 | 미작성 |
| (DB) | - | 회원, 사진, 결과 기록 저장 | 서버 담당자 | 미작성 |

## 임시 결정 사항 (서버 담당자와 재협의 필요)

- 로그인 확인 없이 동작 (명세상 "로그인 필요" 주소 포함)
- DB 없이 파일로 저장 (`storage/images/` 올린 사진, `storage/extractions/` 추출 결과, `storage/jobs/` 합성 작업, `storage/results/` 합성 결과, 저장소 제외)
- 합성 작업 상태는 서버 메모리에 보관 → 서버 재시작 시 진행 중이던 작업은 실패(`SERVER_RESTARTED`)로 표시
- 파일 보기(`/api/files`) 보호 없음 → 누구나 열람 가능. 보호 방식은 명세 7장 미정

## 명세 외 추가 (제안, 팀 합의 필요)

- 상의 추출(`/api/extract`)에 `box` 선택 값 추가 (2026-10-13): `{ x1, y1, x2, y2 }` 0~1 비율. 점만 / 박스만 / 박스 + 점 가능. 기존 점만 요청은 그대로 동작
