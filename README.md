# MOA (CGI_MOA)

- 상의 사진에서 옷을 골라 인물 사진에 입혀 주는 웹 서비스
- 흐름: 상의 사진 고르기 → 인물 사진 고르기 → 점 찍어 상의 추출(SAM2) → 입힐 영역 지정 → 합성(AnyDoor) → 결과 저장

## 폴더와 문서 안내

```
CGI_V2/
├── README.md                          지금 이 문서. 소개, 현재 상태, 실행 방법
│
├── docs/                              팀 공용 문서
│   ├── api.md                         팀 API 명세: 화면 ↔ 서버가 주고받는 값, 정한 것/정할 것
│   ├── environment.md                 파이썬 가상환경(CGI) 설치 방법
│   ├── pip_freeze.txt                 설치된 패키지 전체 목록 (environment.md 부록)
│   ├── database.md                    MySQL 설정: DB·계정 만들기, .env, 문제 해결
│   ├── login_extend.md                로그인 시간 연장 규칙 (만료 30분 전·10분 전 확인)
│   └── ui_handoff.md                  화면 담당 전달 사항 (날짜별 할 일 체크리스트)
│
├── frontend/                          웹 화면 (React)
│   ├── README.md                      화면 실행 방법
│   └── .env.example                   화면이 쓸 서버 고르기 (mock / mixed / real)
│
├── backend/                           서버 (FastAPI): 로그인, 사진 올리기, 추출, 합성, 사진첩
│   ├── README.md                      서버 파일별 역할·상태, 임시 결정, 명세 외 추가
│   └── .env.example                   DB 접속 정보 본보기 (복사해서 .env로)
│
├── features/                          AI 기능
│   ├── object_extraction/README.md    SAM2 상의 추출: 호출 방법, 모델 파일 위치
│   └── composition/README.md          AnyDoor 합성: 호출 방법, 필요한 모델 파일, 속도
│
└── scripts/                           서버·화면 없이 AI 기능만 시험
    └── README.md                      test_object_extraction.py, test_compose.py 사용법
```

**하려는 일별로 볼 문서**

| 하려는 일 | 문서 (순서대로) |
|---|---|
| 처음 받아서 실행하기 | 이 문서 "실행" → [docs/environment.md](docs/environment.md) → [docs/database.md](docs/database.md) |
| 화면 작업 (화면 담당) | [docs/ui_handoff.md](docs/ui_handoff.md) → [docs/api.md](docs/api.md) → [frontend/README.md](frontend/README.md) |
| 서버 주소·주고받는 값 확인 | [docs/api.md](docs/api.md) → [backend/README.md](backend/README.md) "명세 외 추가" |
| 로그인이 안 될 때 | [docs/database.md](docs/database.md) "문제 해결" |
| AI 기능만 따로 시험 | [scripts/README.md](scripts/README.md) → [features/](features/) 아래 README |

## 현재 상태 (2026-10-15)

| 부분 | 상태 |
|---|---|
| 화면 | 시안 완성 |
| 서버: 사진 올리기, 상의 추출(SAM2), 합성(AnyDoor) | 동작 확인 |
| 서버: 사진첩 (결과 목록, 저장/좋아요, 저장 안 한 결과 3일 뒤 삭제) | 동작 확인 |
| 서버: 로그인, 회원가입, 내 정보, 로그아웃 (MySQL), 로그인 시간 연장 | 동작 확인 |
| 화면 ↔ 서버 연결 | 로그인, 사진 올리기, 추출, 합성, 사진첩 연결 완료 |
| 화면에 붙일 것 | 로그인 연장 안내 창, 회원가입 버튼 등 → [docs/ui_handoff.md](docs/ui_handoff.md) |

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
- MySQL 설정 (로그인용, 처음 한 번): [docs/database.md](docs/database.md). 없어도 서버는 켜지고 로그인만 안 됨
- 실행 (저장소 맨 위 폴더): `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`
- 확인: http://localhost:8000/api/health → `{"status":"ok"}`, 시험 화면 http://localhost:8000/docs
- GPU 필요 (확인 환경: RTX 3080 10GB). 서버가 켜질 때 AnyDoor를 미리 불러와 예열(1~2분), 이후 합성 1장 약 1분

**화면**
- Node.js 필요
- `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173

## 화면과 서버 함께 쓰기

- `frontend/.env.example`을 `frontend/.env.local`로 복사하고 `VITE_API_MODE=mixed`로 변경
  - `mixed`: 서버에 있는 기능(로그인, 사진 올리기, 추출, 합성, 사진첩)은 실제 서버로
  - `mock`(기본): 서버 없이 화면만 볼 때
- 순서: 서버 실행 → 화면 실행(`npm run dev`) → http://localhost:5173 → 로그인 `test` / `test1234` (가짜 서버 `mock`에서는 `test` / `test`)
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
