# MOA (CGI_MOA)

## 1. 개요

- 상의 사진의 옷을 인물 사진에 입혀 주는 웹 서비스
- 처리 흐름: 상의 사진 선택 → 인물 사진 선택 → 상의 추출(SAM2) → 착용 영역 지정 → 합성(AnyDoor) → 결과 저장

## 2. 디렉터리 구성

```
CGI_V2/
├── README.md
├── docs/
│   ├── api.md                       API 명세
│   ├── environment.md               가상환경(CGI) 설치
│   ├── pip_freeze.txt               설치 패키지 전체 목록
│   ├── database.md                  MySQL 설정
│   ├── login_extend.md              로그인 시간 연장 규칙
│   └── ui_handoff.md                프론트엔드 전달 사항
├── frontend/                        프론트엔드 (React)
│   ├── README.md
│   └── .env.example                 연결 서버 설정 (mock / mixed / real)
├── backend/                         백엔드 (FastAPI)
│   ├── README.md                    파일별 역할, 임시 결정
│   └── .env.example                 DB 접속 정보 예시
├── features/
│   ├── object_extraction/README.md  SAM2 상의 추출
│   └── composition/README.md        AnyDoor 합성
└── scripts/README.md                AI 기능 단독 시험
```

## 3. 문서 안내

| 목적 | 참고 문서 (읽는 순서) |
|---|---|
| 최초 실행 | 5장 → [environment.md](docs/environment.md) → [database.md](docs/database.md) |
| 프론트엔드 작업 | [ui_handoff.md](docs/ui_handoff.md) → [api.md](docs/api.md) |
| API 확인 | [api.md](docs/api.md) → [backend/README.md](backend/README.md) |
| 로그인 오류 | [database.md](docs/database.md) "문제 해결" |
| AI 기능 단독 시험 | [scripts/README.md](scripts/README.md) |

## 4. 역할 분담

| 영역 | 폴더 | 담당 |
|---|---|---|
| 프론트엔드 (웹 화면) | `frontend/` | 화면 담당 |
| 백엔드 (API 서버), AI 기능 (SAM2, AnyDoor) | `backend/`, `features/` | AI 기능·서버 담당 |

## 5. 실행 방법

### 5-1. 백엔드 (API 서버)

- 사전 준비
  - `CGI` 가상환경: [environment.md](docs/environment.md)
  - MySQL: [database.md](docs/database.md)
  - GPU, 모델 파일 (저장소 미포함, AI 기능·서버 담당에게 요청)
- 실행 (저장소 최상위 폴더): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인: http://localhost:8000/api/health → `{"status":"ok"}`, API 시험 화면 http://localhost:8000/docs
- 시작 시 AnyDoor 예열 1~2분, 합성 1장 약 1분

### 5-2. 프론트엔드 (웹 화면)

- 사전 준비: Node.js

| 순서 | 명령 | 동작 |
|---|---|---|
| 1 | `cd frontend` | 프론트엔드 폴더로 이동 |
| 2 | `npm install` | 필요한 패키지 설치 (최초 1회) |
| 3 | `npm run dev` | 개발 서버 실행 |
| 4 | http://localhost:5173 | 브라우저에서 접속 |

### 5-3. 백엔드 연동

- `frontend/.env.example`을 `frontend/.env.local`로 복사 후 `VITE_API_MODE=mixed`
- 백엔드 실행 → 프론트엔드 실행 → 로그인 `test` / `test1234`

## 6. 저장소 제외 항목

- `.gitignore` 등록: `CGI/`(가상환경), `checkpoints/`(모델 파일), `storage/`(업로드·결과 파일), `backend/.env`, `frontend/.env.local`(개인 설정)
- VITON-HD 데이터 (연구용 라이선스)
