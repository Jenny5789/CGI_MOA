# MOA (CGI_MOA)

- 상의 사진의 옷을 인물 사진에 입혀 주는 웹 서비스
- 흐름: 상의 사진 → 인물 사진 → 상의 추출(SAM2) → 입힐 영역 지정 → 합성(AnyDoor) → 저장

## 폴더와 문서

```
CGI_V2/
├── README.md
├── docs/
│   ├── api.md                       API 명세
│   ├── environment.md               가상환경(CGI) 설치
│   ├── pip_freeze.txt               설치 패키지 전체 목록
│   ├── database.md                  MySQL 설정
│   ├── login_extend.md              로그인 시간 연장 규칙
│   └── ui_handoff.md                화면 담당 전달 사항
├── frontend/                        웹 화면 (React)
│   ├── README.md
│   └── .env.example                 서버 고르기 (mock / mixed / real)
├── backend/                         서버 (FastAPI)
│   ├── README.md                    파일별 역할, 임시 결정
│   └── .env.example                 DB 접속 정보 본보기
├── features/
│   ├── object_extraction/README.md  SAM2 상의 추출
│   └── composition/README.md        AnyDoor 합성
└── scripts/README.md                AI 기능 단독 시험
```

| 하려는 일 | 문서 |
|---|---|
| 처음 실행 | 아래 "실행" → [environment.md](docs/environment.md) → [database.md](docs/database.md) |
| 화면 작업 | [ui_handoff.md](docs/ui_handoff.md) → [api.md](docs/api.md) |
| 서버 주소 확인 | [api.md](docs/api.md), [backend/README.md](backend/README.md) |
| 로그인 안 됨 | [database.md](docs/database.md) "문제 해결" |
| AI 기능만 시험 | [scripts/README.md](scripts/README.md) |

## 현재 상태 (2026-10-15)

| 부분 | 상태 |
|---|---|
| 서버: 로그인, 사진 올리기, 추출, 합성, 사진첩 | 동작 확인 |
| 화면 ↔ 서버 연결 | 완료 |
| 화면에 붙일 것 | [ui_handoff.md](docs/ui_handoff.md) |

## 담당

| 부분 | 담당 |
|---|---|
| `frontend/` | 화면 담당 |
| `features/`, `backend/` | AI 기능·서버 담당 |

## 실행

**서버**
- 필요: `CGI` 가상환경([environment.md](docs/environment.md)), GPU, 모델 파일(저장소에 없음, AI 기능·서버 담당에게 받기)
- MySQL 설정: [database.md](docs/database.md) (없으면 로그인만 안 됨)
- 실행 (저장소 맨 위 폴더): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인: http://localhost:8000/api/health → `{"status":"ok"}` / 시험 화면 http://localhost:8000/docs
- 켤 때 AnyDoor 예열 1~2분, 합성 1장 약 1분

**화면**
- 필요: Node.js
- `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173

## 화면과 서버 함께 쓰기

- `frontend/.env.example` → `frontend/.env.local`로 복사, `VITE_API_MODE=mixed`
- 서버 실행 → 화면 실행 → 로그인 `test` / `test1234`

## 저장소에 올리지 않는 것

- `CGI/`, `checkpoints/`, `storage/`, `backend/.env`, `frontend/.env.local` (`.gitignore`)
- VITON-HD 데이터 (연구용 라이선스)
