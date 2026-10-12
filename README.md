# MOA (CGI_MOA)

- 상의 사진에서 옷을 골라 인물 사진에 입혀 주는 웹 서비스
- 흐름: 상의 사진 고르기 → 인물 사진 고르기 → 점 찍어 상의 추출(SAM2) → 입힐 영역 지정 → 합성(AnyDoor) → 결과 저장

## 폴더 구조

| 폴더 | 내용 | 설명서 |
|---|---|---|
| `frontend/` | 웹 화면 (React) | [frontend/README.md](frontend/README.md) |
| `backend/` | 서버 (FastAPI). 사진 올리기, 상의 추출, 합성 | [backend/README.md](backend/README.md) |
| `features/` | AI 기능. SAM2 상의 추출, AnyDoor 합성 | [features/object_extraction/README.md](features/object_extraction/README.md) |
| `scripts/` | 서버·화면 없이 AI 기능만 확인하는 스크립트 | [scripts/README.md](scripts/README.md) |
| `docs/` | 팀 API 명세, 환경 설치 방법 | [docs/api.md](docs/api.md), [docs/environment_2026-10-11.md](docs/environment_2026-10-11.md) |

## 현재 상태 (2026-10-12)

| 부분 | 상태 |
|---|---|
| 화면 | 시안 완성. 추출·합성은 아직 흉내만 냄 (서버 미연결) |
| 서버: 사진 올리기, 상의 추출, 합성 | 동작 확인 (`/docs` 시험 화면 기준) |
| 서버: 로그인, 회원, 사진첩 저장, DB | 미작성 (서버 담당) |
| 화면 ↔ 서버 연결 | 예정 |

## 담당

| 부분 | 담당 |
|---|---|
| `frontend/` 화면 | 화면 담당 |
| `features/`, `backend/routers/extract.py`, `backend/routers/compose.py` | AI 기능 담당 |
| `backend/` 나머지 (로그인, DB, 사진첩) | 서버 담당 |

- 서버 파일별 담당과 임시 결정 사항: [backend/README.md](backend/README.md)

## 실행

**화면**
- Node.js 필요
- `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173

**서버**
- `CGI` 가상환경 필요 (Python 3.10, torch 2.5.1, SAM2, AnyDoor 패키지): [docs/environment_2026-10-11.md](docs/environment_2026-10-11.md)
- 모델 파일(SAM2, AnyDoor)은 용량이 커서 저장소에 없음 → 추출·합성을 실행할 때 AI 기능 담당에게 받기
- 실행 (저장소 맨 위 폴더): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인: http://localhost:8000/docs
- GPU 필요 (확인 환경: RTX 3080 10GB). 합성 1장 약 2분, 서버 시작 후 첫 합성은 약 4분

## 저장소에 올리지 않는 것

- 가상환경(`CGI/`), 모델 파일(`checkpoints/`), 서버 저장 폴더(`storage/`): `.gitignore`에 등록
- VITON-HD 데이터: 연구용 라이선스, 학습 데이터로만 사용
