# MOA (CGI_MOA)

- 상의 사진에서 옷을 골라 인물 사진에 입혀 주는 웹 서비스
- 흐름: 상의 사진 고르기 → 인물 사진 고르기 → 점 찍어 상의 추출(SAM2) → 입힐 영역 지정 → 합성(AnyDoor) → 결과 저장

## 폴더 구조

| 폴더 | 내용 | 설명서 |
|---|---|---|
| `frontend/` | 웹 화면 (React) | [frontend/README.md](frontend/README.md) |
| `backend/` | 서버 (FastAPI). 사진 올리기, 상의 추출, 합성, 사진첩 | [backend/README.md](backend/README.md) |
| `features/` | AI 기능. SAM2 상의 추출, AnyDoor 합성 | [features/object_extraction/README.md](features/object_extraction/README.md) |
| `scripts/` | 서버·화면 없이 AI 기능만 확인하는 스크립트 | [scripts/README.md](scripts/README.md) |
| `docs/` | 팀 API 명세, 환경 설치 방법 | [docs/api.md](docs/api.md), [docs/environment.md](docs/environment.md) |

## 현재 상태 (2026-10-14)

| 부분 | 상태 |
|---|---|
| 화면 | 시안 완성 |
| 서버: 사진 올리기, 상의 추출(SAM2), 합성(AnyDoor) | 동작 확인 |
| 서버: 사진첩 (결과 목록, 저장/좋아요, 저장 안 한 결과 3일 뒤 삭제) | 동작 확인 |
| 화면 ↔ 서버 연결 | 사진 올리기, 추출, 합성, 사진첩 연결 완료 |
| 로그인 | 아직 화면 안의 가짜 로그인 사용 (`test` / `test`) |

## 담당

| 부분 | 담당 |
|---|---|
| `frontend/` 화면 | 화면 담당 |
| `features/` (SAM2, AnyDoor), `backend/` 서버 | AI 기능·서버 담당 |

- 서버 파일별 내용과 임시 결정 사항: [backend/README.md](backend/README.md)

## 실행

**서버**
- `CGI` 가상환경 필요 (Python 3.10, torch 2.5.1, SAM2, AnyDoor 패키지): [docs/environment.md](docs/environment.md)
- 모델 파일(SAM2, AnyDoor)은 용량이 커서 저장소에 없음 → 추출·합성을 실행할 때 AI 기능·서버 담당에게 받기
- 실행 (저장소 맨 위 폴더): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인: http://localhost:8000/api/health → `{"status":"ok"}`, 시험 화면 http://localhost:8000/docs
- GPU 필요 (확인 환경: RTX 3080 10GB). 서버가 켜질 때 AnyDoor를 미리 불러와 예열(1~2분), 이후 합성 1장 약 1분

**화면**
- Node.js 필요
- `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173

## 화면과 서버 함께 쓰기

- `frontend/.env.example`을 `frontend/.env.local`로 복사하고 `VITE_API_MODE=mixed`로 변경
  - `mixed`: 서버에 있는 기능(사진 올리기, 추출, 합성, 사진첩)은 실제 서버로, 로그인은 화면 안의 가짜 서버로
  - `mock`(기본): 서버 없이 화면만 볼 때
- 순서: 서버 실행 → 화면 실행(`npm run dev`) → http://localhost:5173 → 로그인 `test` / `test`
- 합성하기
  1. 상의 사진 → "이 사진 사용" (서버에 올라감)
  2. 인물 사진 → "이 사진 사용"
  3. 상의 위에 점 찍기 (왼쪽 클릭 포함 / 오른쪽 클릭 제외) → 확인 → SAM2가 찾은 상의 영역 확인·다듬기
  4. 입힐 곳(인물의 상의) 지정 → 합성 시작 → "합성 중 (NN%)" → 결과
  5. 결과 "저장" → 마이페이지 사진첩 "전체", 합성하기 "내 작업 기록"에 표시
- 저장하지 않은 결과는 마이페이지 "최근 작업"에 3일 동안 남음

## 저장소에 올리지 않는 것

- 가상환경(`CGI/`), 모델 파일(`checkpoints/`), 서버 저장 폴더(`storage/`), 화면 설정(`frontend/.env.local`): `.gitignore`에 등록
- VITON-HD 데이터: 연구용 라이선스, 학습 데이터로만 사용
