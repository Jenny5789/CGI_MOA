# MOA (CGI_MOA)

## 1. 개요

- 상의 사진 속 옷을 인물 사진 속 사람에게 입혀 주는 웹 서비스
- 처리 흐름

| 순서 | 단계 | 처리 |
|---|---|---|
| 1 | 상의 사진 선택 | 사용자가 옷 사진을 올림 |
| 2 | 인물 사진 선택 | 사용자가 옷을 입힐 사람 사진을 올림 |
| 3 | 상의 추출 | 사용자가 옷 위에 점을 찍으면 AI(SAM2)가 옷 부분만 잘라 냄 |
| 4 | 착용 영역 지정 | 사용자가 인물 사진에서 옷을 입힐 부위를 칠함 |
| 5 | 합성 | AI(AnyDoor)가 잘라 낸 옷을 칠한 부위에 자연스럽게 입힘 |
| 6 | 결과 저장 | 마음에 드는 결과를 사진첩에 저장 |

## 2. 용어

| 용어 | 뜻 |
|---|---|
| 프론트엔드 | 사용자가 브라우저에서 보는 웹 화면 (`frontend/`) |
| 백엔드 | 화면의 요청을 받아 AI 처리·저장을 하는 서버 프로그램 (`backend/`) |
| API | 프론트엔드와 백엔드가 데이터를 주고받는 약속 (주소, 보내는 값, 받는 값) |
| AI 기능 | 이 프로젝트에서 쓰는 AI 모델 2개: SAM2(상의 추출), AnyDoor(합성) (`features/`) |
| SAM2 | 사진에서 지정한 물체의 영역을 찾아내는 AI 모델 (Meta) |
| AnyDoor | 한 사진의 물체를 다른 사진에 자연스럽게 넣는 AI 모델 |
| 가상환경 (`CGI`) | 이 프로젝트 전용 파이썬과 패키지를 따로 설치해 둔 폴더 |
| MySQL | 회원 정보·로그인 기록을 저장하는 데이터베이스(DB) |
| 모델 파일 | AI 모델이 학습한 결과 파일 (수 GB, 저장소에 없음) |

## 3. 디렉터리 구성

```
CGI_V2/
├── README.md                        이 문서
├── docs/                            공용 문서
│   ├── api.md                       API 명세
│   ├── environment.md               가상환경 설치 방법
│   ├── pip_freeze.txt               설치된 파이썬 패키지 전체 목록
│   ├── database.md                  MySQL 설정 방법
│   ├── login_extend.md              로그인 시간 연장 규칙
│   └── ui_handoff.md                프론트엔드 담당에게 전달하는 작업 목록
├── frontend/                        프론트엔드 (React)
│   ├── README.md                    프론트엔드 설명
│   └── .env.example                 연결할 백엔드 설정 예시
├── backend/                         백엔드 (FastAPI)
│   ├── README.md                    백엔드 파일별 역할
│   └── .env.example                 DB 접속 정보 예시
├── features/                        AI 기능
│   ├── object_extraction/README.md  SAM2 상의 추출 사용법
│   └── composition/README.md        AnyDoor 합성 사용법
└── scripts/README.md                AI 기능만 따로 시험하는 방법
```

## 4. 문서 안내

| 목적 | 참고 문서 (읽는 순서) |
|---|---|
| 프로젝트를 처음 내려받아 실행 | 6장 실행 방법 → [environment.md](docs/environment.md) → [database.md](docs/database.md) |
| 웹 화면 개발 | [ui_handoff.md](docs/ui_handoff.md) → [api.md](docs/api.md) |
| 백엔드가 제공하는 기능·주소 확인 | [api.md](docs/api.md) → [backend/README.md](backend/README.md) |
| 로그인이 안 될 때 | [database.md](docs/database.md)의 "문제 해결" (오류 메시지별 조치) |
| 웹 화면·서버 없이 AI 기능(상의 추출, 합성)만 시험 | [scripts/README.md](scripts/README.md) |

## 5. 역할 분담

| 영역 | 폴더 | 담당 |
|---|---|---|
| 프론트엔드 | `frontend/` | 화면 담당 |
| 백엔드, AI 기능 | `backend/`, `features/` | AI 기능·서버 담당 |

## 6. 실행 방법

### 6-1. 백엔드

- 사전 준비
  - 가상환경 `CGI`: [environment.md](docs/environment.md)
  - MySQL: [database.md](docs/database.md)
  - GPU, 모델 파일 (AI 기능·서버 담당에게 요청)
- 실행 (저장소 최상위 폴더에서): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인
  - http://localhost:8000/api/health → `{"status":"ok"}`이면 정상
  - http://localhost:8000/docs → API를 직접 시험하는 화면
- 시작 후 AI 모델을 불러오는 데 1~2분, 합성 1장 약 1분

### 6-2. 프론트엔드

- 사전 준비: Node.js

| 순서 | 명령 | 동작 |
|---|---|---|
| 1 | `cd frontend` | 프론트엔드 폴더로 이동 |
| 2 | `npm install` | 필요한 패키지 설치 (최초 1회) |
| 3 | `npm run dev` | 웹 화면 실행 |
| 4 | http://localhost:5173 | 브라우저에서 접속 |

### 6-3. 프론트엔드와 백엔드 연결

- 기본 상태: 프론트엔드가 백엔드 없이 가짜 데이터로 동작
- 실제 백엔드에 연결: `frontend/.env.example`을 `frontend/.env.local`로 복사 후 `VITE_API_MODE=mixed`
- 백엔드 실행 → 프론트엔드 실행 → 로그인 `test` / `test1234`

## 7. 저장소 제외 항목

- `.gitignore`에 등록되어 GitHub에 올라가지 않는 것
  - `CGI/`: 가상환경
  - `checkpoints/`: 모델 파일
  - `storage/`: 사용자가 올린 사진, 합성 결과
  - `backend/.env`, `frontend/.env.local`: 개인 설정 (DB 비밀번호 등)
- VITON-HD 데이터: 연구용 라이선스라 공유하지 않음
