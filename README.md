# MOA (CGI_MOA)

## 1. 개요

- 상의 이미지의 의류를 인물 이미지에 합성하는 웹 서비스
- 처리 절차

| 순서 | 단계 | 내용 |
|---|---|---|
| 1 | 상의 이미지 업로드 | 합성할 의류 이미지 입력 |
| 2 | 인물 이미지 업로드 | 의류를 착용시킬 인물 이미지 입력 |
| 3 | 상의 영역 추출 | 사용자 지정 좌표 기반 의류 영역 분할 (SAM2) |
| 4 | 착용 영역 지정 | 인물 이미지 내 합성 위치 지정 |
| 5 | 이미지 합성 | 추출 의류를 착용 영역에 합성 (AnyDoor) |
| 6 | 결과 저장 | 합성 결과를 사진첩에 저장 |

## 2. 디렉터리 구성

```
CGI_V2/
├── README.md                        프로젝트 개요
├── docs/                            공용 문서
│   ├── api.md                       API 명세
│   ├── environment.md               개발 환경 구축
│   ├── pip_freeze.txt               Python 패키지 목록
│   ├── database.md                  데이터베이스(MySQL) 구축
│   ├── login_extend.md              로그인 세션 연장 정책
│   └── ui_handoff.md                프론트엔드 전달 사항
├── frontend/                        프론트엔드 (React)
│   ├── README.md                    프론트엔드 개요
│   └── .env.example                 백엔드 연결 설정 예시
├── backend/                         백엔드 (FastAPI)
│   ├── README.md                    백엔드 구성
│   └── .env.example                 데이터베이스 접속 설정 예시
├── features/                        AI 모듈
│   ├── object_extraction/README.md  상의 영역 추출 모듈 (SAM2)
│   └── composition/README.md        이미지 합성 모듈 (AnyDoor)
└── scripts/README.md                AI 모듈 단위 테스트
```

## 3. 문서 안내

| 목적 | 참고 문서 (열람 순서) |
|---|---|
| 개발 환경 구축 및 최초 실행 | 5장 → [environment.md](docs/environment.md) → [database.md](docs/database.md) |
| 프론트엔드 개발 | [ui_handoff.md](docs/ui_handoff.md) → [api.md](docs/api.md) |
| API 사양 확인 | [api.md](docs/api.md) → [backend/README.md](backend/README.md) |
| 로그인 장애 조치 | [database.md](docs/database.md) "문제 해결" |
| AI 모듈 단위 테스트 | [scripts/README.md](scripts/README.md) |

## 4. 역할 분담

| 영역 | 디렉터리 | 담당 |
|---|---|---|
| 프론트엔드 | `frontend/` | 화면 담당 |
| 백엔드, AI 모듈 | `backend/`, `features/` | AI 기능·서버 담당 |

## 5. 실행 방법

### 5-1. 백엔드

- 사전 요건
  - Python 가상환경 `CGI`: [environment.md](docs/environment.md)
  - MySQL: [database.md](docs/database.md)
  - GPU, 모델 가중치 파일 (저장소 미포함, AI 기능·서버 담당에게 요청)
- 실행 (저장소 최상위 디렉터리): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 동작 확인
  - http://localhost:8000/api/health → `{"status":"ok"}`
  - http://localhost:8000/docs → API 테스트 페이지
- 소요 시간: 기동 시 모델 로딩 1~2분, 합성 1건 약 1분

### 5-2. 프론트엔드

- 사전 요건: Node.js

| 순서 | 명령 | 내용 |
|---|---|---|
| 1 | `cd frontend` | 프론트엔드 디렉터리 이동 |
| 2 | `npm install` | 의존 패키지 설치 (최초 1회) |
| 3 | `npm run dev` | 개발 서버 실행 |
| 4 | http://localhost:5173 | 브라우저 접속 |

### 5-3. 프론트엔드·백엔드 연동

- 기본값: 모의(mock) 데이터로 동작
- 연동 설정: `frontend/.env.example`을 `frontend/.env.local`로 복사 후 `VITE_API_MODE=mixed`
- 실행 순서: 백엔드 → 프론트엔드 → 테스트 계정 `test` / `test1234` 로그인

## 6. 저장소 제외 항목

| 항목 | 내용 | 사유 |
|---|---|---|
| `CGI/` | Python 가상환경 | 개인 환경 |
| `checkpoints/` | 모델 가중치 파일 | 대용량 |
| `storage/` | 업로드 이미지, 합성 결과 | 사용자 데이터 |
| `backend/.env`, `frontend/.env.local` | 개인 설정 (DB 비밀번호 등) | 보안 |
| VITON-HD | 학습 데이터셋 | 연구용 라이선스 |
