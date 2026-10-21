<div align="center">

# MOA

### AI 기반 상의 착용 합성 웹 서비스

상의 사진과 인물 사진을 고르고 영역을 지정하면, AI가 상의를 인물에게 입힌 사진을 만들어 주는 서비스입니다.

**팀 프로젝트 · Frontend / Backend / AI**

`React + Vite` · `FastAPI` · `MySQL` · `SAM2` · `AnyDoor` · `PyTorch`

<br>

<img src="docs/readme/moa_home.jpg" alt="MOA 홈 화면" width="88%">

</div>

---

## 1. 프로젝트 개요

MOA는 **직접 입어 보지 않아도, 마음에 드는 상의를 내 사진 위에 합성해 착용한 모습을 미리 확인하는 웹 서비스**입니다.

사용자가 상의 사진에서 상의를 점으로 지정하면 SAM2가 상의 영역을 잘라 내고, 인물 사진에서 입힐 영역을 지정하면 AnyDoor가 그 자리에 상의를 입힌 사진을 만듭니다. 결과는 회원별 사진첩에 저장해 다시 볼 수 있습니다.

| 항목 | 내용 |
|---|---|
| **문제** | 직접 착용의 시간·공간·비용 제약, 기존 합성의 부자연스러운 결과와 편집 기술 부담 |
| **목표** | 사진 선택 → 상의 영역 추출 → 착용 합성 → 사진첩 저장까지 하나의 웹 흐름으로 연결 |
| **기간** | 2026.09.28 ~ 2026.11.22 |
| **구성** | 4인 팀 프로젝트, 역할은 [7장 역할 분담](#7-역할-분담) |

### Tech Stack

| 영역 | 기술 |
|---|---|
| **Languages** | Python 3.10, JavaScript |
| **Frontend** | React 19, Vite 6, React Router 6 |
| **Backend / API** | FastAPI, Uvicorn |
| **AI / Computer Vision** | SAM2 `sam2.1_hiera_base_plus`, AnyDoor (DINOv2 · ControlNet · Stable Diffusion) |
| **Inference** | PyTorch 2.5.1 · CUDA 12.1, xformers, float16 혼합 정밀도 |
| **Database / Auth** | MySQL 8, SQLAlchemy, PyMySQL, 토큰 로그인 |

### 실행 환경 및 지원 범위

| 영역 | 현재 범위 |
|---|---|
| Web | 데스크톱 브라우저 1440px 폭, 휴대폰 375px 폭 반응형 화면 |
| AI 추론 | NVIDIA GPU 필요. RTX 3080 10GB에서 확인, 합성 중 PyTorch 최대 할당 8.25GB |
| 운영체제 | Windows 11에서 개발·확인 |
| 배포 | 로컬 개발 서버, 외부 접속은 Cloudflare 터널로 시연 |

---

## 2. 서비스 구조

화면은 서버의 `/api`만 부르고, 서버가 DB · 파일 저장소 · GPU의 AI 모듈을 연결합니다.

<p align="center">
  <img src="docs/readme/moa_architecture.png" alt="MOA 서비스 구조" width="100%">
</p>

| 구성 | 역할 |
|---|---|
| Frontend `frontend/` | React 웹 화면. 모든 서버 요청은 `src/api/`를 거치며 로그인 토큰을 붙임 |
| Backend `backend/` | FastAPI 서버. 로그인, 사진 업로드, 추출, 합성 작업 대기열, 결과·사진첩 |
| AI 모듈 `features/` | `object_extraction`: SAM2 상의 영역 추출 / `composition`: AnyDoor 착용 합성과 후처리 |
| MySQL | 회원 `users`, 로그인 토큰 `sessions` |
| `storage/` | 올린 사진, 추출 윤곽, 합성 결과. 저장하지 않은 결과는 24시간 뒤 삭제 |

---

## 3. 처리 흐름

| 순서 | 단계 | 내용 |
|---|---|---|
| 1 | 상의 이미지 업로드 | 합성할 의류 이미지 입력 |
| 2 | 인물 이미지 업로드 | 의류를 착용시킬 인물 이미지 입력 |
| 3 | 상의 영역 추출 | 사용자 지정 좌표 기반 SAM2 의류 영역 분할 |
| 4 | 착용 영역 지정 | 인물 이미지 내 합성 위치 지정 |
| 5 | 이미지 합성 | 추출 의류를 착용 영역에 AnyDoor로 합성 |
| 6 | 결과 저장 | 합성 결과를 사진첩에 저장 |

### 합성 요청 흐름

```text
Frontend
  ↓ POST /api/images        상의 사진, 인물 사진 업로드
  ↓ POST /api/extract       상의에 찍은 점 → SAM2 상의 영역
  ↓ POST /api/compose       추출 결과 + 입힐 영역 → AnyDoor 합성 작업 등록
  ↓ GET  /api/jobs/{id}     2초마다 진행률 확인: 대기 순서, %
  ↓ GET  /api/results/{id}  합성 결과
  ↓ PATCH /api/results/{id} 사진첩에 저장 / 좋아요
Backend ↔ MySQL · storage/ · GPU
```

- 모든 주소의 요청·응답·오류 형식: [docs/api.md](docs/api.md)
- 로그인 토큰은 3시간 유효, 연장 규칙: [docs/login_extend.md](docs/login_extend.md)

---

## 4. 실제 구현 화면

### Web Service

<p align="center">
  <img src="docs/readme/moa_screens.jpg" alt="MOA 주요 화면" width="100%">
</p>

### 합성하기 단계별 화면

실제 서버의 SAM2, AnyDoor에 연결한 상태에서 처음부터 끝까지 진행한 화면입니다.

<p align="center">
  <img src="docs/readme/moa_studio_flow.jpg" alt="MOA 합성하기 단계별 화면" width="100%">
</p>

### 합성 결과

<p align="center">
  <img src="docs/readme/moa_before_after.jpg" alt="상의 사진, 인물 사진, 합성 결과" width="100%">
</p>

- 예시 사진은 모두 AI로 만든 이미지입니다.
- 가슴 앞의 노란 물체는 합성 과정에서 생긴 것이며, 원인은 [9장](#9-known-issues)에 정리했습니다.

---

## 5. 핵심 기능

### 상의 영역 추출 · SAM2

- 상의 사진에 **포함 점**은 왼쪽 클릭, **제외 점**은 오른쪽 클릭으로 찍으면 SAM2가 상의 영역을 분할
- 추출 결과를 **다듬기 창**에서 브러시·지우개로 수정, 휠 확대·끌기 이동으로 경계 정밀 보정
- 설명: [features/object_extraction/README.md](features/object_extraction/README.md)

### 착용 합성 · AnyDoor

- 인물 사진에서 입힐 영역을 점으로 지정하고 다듬기 창에서 보정한 뒤 합성 시작
- 합성 설정 2가지: 상의 경계 보정, 영역 모양 유지
- 서버는 합성 요청을 작업 대기열로 처리하고 진행률과 대기 순서를 알려 줌
- 생성 50스텝, 재생성 범위 1.3배 고정, float16 혼합 정밀도, 구성 요소별 GPU 순차 적재, 서버 시작 시 예열
- 후처리
  - 원본 복원: 착용 영역 위쪽의 얼굴·머리·배경을 원본으로 되돌림, `MOA_RESTORE_ORIGINAL`
  - 박스 선 보정: AnyDoor가 다시 그린 사각형 테두리의 밝기·색 차이 완화, `MOA_SEAM_FIX`
- 설명: [features/composition/README.md](features/composition/README.md)

### 계정과 사진첩

- 로그인 · 회원가입 · 내 정보 · 로그아웃, 비밀번호는 MySQL에 해시로 저장
- 합성 결과 자동 기록: 합성하기 화면 '내 작업 기록', 저장 시 마이페이지 사진첩 이동, 미저장 결과 24시간 후 자동 삭제
- 사진첩: 전체·좋아요 탭, 날짜 선택, 최신순·오래된순 정렬, 사진별 ⋯ 메뉴의 크게 보기·다운로드

### 마이페이지 내 정보·설정·고객센터

- 내 정보: 상자 하나에 프로필 사진·이름·이메일과 계정 설정 탭. 기본 탭은 프로필 수정
- 계정 설정 탭
  - 프로필 수정: 프로필 사진·이름·휴대폰 번호·소개 글. 프로필 사진은 중앙 정사각형 256px, EXIF 미저장
  - 이메일 변경: 현재 비밀번호 기반 본인 확인, 중복 이메일 차단
  - 비밀번호 변경: 변경 기기 로그인 유지, 타 기기 세션 일괄 만료
- 설정: 왼쪽 메뉴, 브라우저 로컬 저장
  - 알림 설정: 합성 완료 시점에 다른 탭 사용 중이면 브라우저 알림 표시
  - 합성 기본 설정: 합성 설정 창의 상의 경계 보정·영역 모양 유지 기본값 지정
- 고객센터: 자주 묻는 질문 7개, 이메일 문의 링크. 예시 주소 teamcgi_moa@example.com, 실제 운영 시 팀 주소로 교체
- API: [docs/api.md 2-7~2-10](docs/api.md#2-7-프로필-수정-추가-제안)

---

## 6. 합성 속도 개선

AnyDoor 공식 설정 그대로는 RTX 3080 10GB에서 사진 한 장, 50스텝 합성에 11~15분이 걸렸습니다. 같은 사진·같은 조건에서 아래 단계를 거쳐 **약 25초**로 줄였습니다.

| 단계 | 변경 내용 | 한 장 합성 시간 |
|---|---|---|
| 공식 설정 | 기준 | 11~15분, 스텝당 13~18초 |
| 시스템 메모리 적재 | 16.8GB 체크포인트를 GPU에서 바로 열면서 VRAM 용량을 초과하던 문제 해결. 시스템 메모리에서 열고 가중치 약 9.2GB만 GPU 적재 | 2분 30초 ~ 3분 45초 |
| 혼합 정밀도 | 행렬 곱 · 합성곱 · 어텐션만 float16으로 계산 | 약 48초 ~ 1분 |
| 서버 시작 시 예열 | 첫 실행에만 느린 GPU 준비 구간을 서버 시작 시 미리 처리 | 첫 요청도 같은 속도 |
| 구성 요소별 GPU 순차 적재 | 사용 중인 구성 요소 묶음만 GPU에 적재, 묶음 교체 시 해제 후 적재 | 약 25초 |

- 화질: float32 대비 float16 결과의 평균 픽셀 차이 0.12~0.17 / 255, 육안 구분 불가 수준. 순차 적재 전후 결과는 픽셀 단위 동일
- 서버 실측 2026-10-21: 합성 요청부터 결과까지 22~26초, 7건. 이전 서버 기록 48~98초

### 구성 요소별 GPU 순차 적재 · 2026-10-21

- 구조: AnyDoor 메모리 절약 모드는 네 구성 요소를 두 묶음으로 나눠 사용 중인 묶음만 GPU에 두는 방식
  - 노이즈 제거 단계: U-Net · ControlNet
  - 전후 단계: VAE · DINOv2
- 기존 동작의 문제
  - 모델 적재 시 네 구성 요소 약 9.2GB 일괄 GPU 적재
  - 묶음 교체 시 새 묶음 적재 후 기존 묶음 해제 → 교체 시점마다 네 구성 요소 동시 상주
  - VRAM 10GB 용량 초과, 공유 GPU 메모리 최대 3.2GB 사용으로 합성 지연
- 변경 내용: `features/composition/anydoor_composer.py`
  - 큰 구성 요소 네 개를 CPU에 둔 상태로 모델 적재
  - 묶음 교체 순서를 기존 묶음 해제 후 새 묶음 적재로 변경
  - 가중치 · 연산 방식 · AnyDoor 원본 파일 변경 없음
- 비교 조건: RTX 3080 10GB, 서버 종료 상태, 같은 입력과 seed, 상의 경계 보정 적용, 예열 → SAM2 추출 → 합성 2회

| 항목 | 기존 | 개선 |
|---|---|---|
| 합성 시간 1회 · 2회 | 41.1초 · 36.9초 | 25.4초 · 24.4초 |
| 합성 시간 평균 | 39.0초 | 24.9초, 36% 단축 |
| 모델 적재 · 예열 | 152.1초 | 100.8초 |
| PyTorch 최대 할당 메모리 | 9.70GB | 8.25GB |
| PyTorch 최대 확보 메모리 | 11.43GB | 9.22GB |
| 공유 GPU 메모리 최대 사용량 | 3,199MB | 218MB |
| 결과 이미지 | 기준 | 픽셀 단위 동일, 최대 차이 0 |

---

## 7. 역할 분담

| 담당 | 맡은 일 |
|---|---|
| 최이재 | 이미지 처리 파이프라인 구성, SAM2 상의 영역 추출·AnyDoor 합성 모듈 구현, 합성 품질 개선: 원본 복원 후처리·추출 후처리·재생성 범위 배율 실험·박스 선 보정, 백엔드 서버·DB 설계·구현, 작업 대기열·GPU 자원 관리, 파일 접근 보안, 프론트엔드·서버 API 연동, API 명세·개발 환경 문서 정리 |
| 서지섭 | UI/UX 설계·프론트엔드 개발, 프론트엔드·서버 API 연동, 이미지 처리 파이프라인 구성·성능 개선, 백엔드 기능 구현, 데이터 전처리 |
| 김기욱 | 합성 결과 평가 기준 수립, Git 저장소 관리 |
| 정의형 | 상의 영역 추출 모델 후보 조사·비교, 모델 학습 방법 연구 |

---

## 8. 검증 결과

| 항목 | 결과 |
|---|---|
| 환경 점검 `scripts/check_env.py` | 18 / 18 통과: 패키지 버전, GPU, 모델 파일, DB 설정 |
| 전체 흐름 · 화면 | 로그인 → 사진 선택·업로드 → 추출 → 합성 → 저장 → 사진첩 확인 |
| 외부 접속 | Cloudflare 터널로 다른 망의 휴대폰에서 로그인·마이페이지·합성 포함 전체 흐름 확인 |
| 상의 추출 | 서버를 켠 뒤 첫 요청 약 27초, 이후 약 2.5~3초 |
| 착용 합성 | 요청부터 결과까지 22~26초 |
| SAM2 정확도 | VITON-HD 테스트 무작위 30쌍, 클릭 1회 → 3회 평균 IoU: 상품 사진 상의 0.89 → 0.96, 착용 상의 0.77 → 0.86 |
| 마이페이지 설정 API · 10/20 | 정상·오류 22개 사례 모두 기대 응답. 형식 오류 400, 중복 이메일 409, 비밀번호 변경 후 타 기기 토큰 401 |
| 마이페이지 화면 · 10/22 | 내 정보·사진첩·계정 설정 화면 전환, 크게 보기, 다운로드, 휴대폰 폭 375px 가로 스크롤 없음 |

- IoU: 정답 영역과 추출 영역이 겹치는 비율, 1에 가까울수록 정확
- 확인 환경: Windows 11, RTX 3080 10GB. 착용 합성은 2026-10-21, SAM2 정확도는 2026-10-17 측정

---

## 9. Known Issues

### 상의 사진 속 자세가 결과에 섞임

- 상의 사진의 사람이 턱을 괴는 등 팔을 들고 있으면, 결과에 **없던 손이나 물체가 생기는 경우**가 있음. 4장 합성 결과의 노란 물체
- 잘라 낸 상의에 팔 모양 빈자리가 남고, AnyDoor가 그 자리를 채우는 것으로 추정

### 상의만 지정해도 사람 전체가 잡힘

- 사람이 입고 있는 상의 사진에서 상의에만 점을 찍으면 SAM2가 **얼굴·머리를 포함한 사람 전체**를 잡는 경우가 있음
- 얼굴 · 머리 · 손에 제외 점을 함께 찍으면 상의만 잡힘

### 원본 복원 경계의 불연속

- 원본 복원은 세로줄마다 착용 영역 최상단을 기준으로 위는 원본, 아래는 합성 결과를 사용
- 팔이 몸통에 붙은 자세나 파인 목선에서 팔·카라 일부만 복원되어 **세로 불연속 경계**나 목 주변 빈 부분이 생기는 경우가 있음
- 담당자 오류 보고 완료, 복원 범위를 합성 영역과 새 상의 영역 안쪽으로 한정하는 방향으로 개선 예정

### 합성 영역이 상의보다 길면 밑단 아래에 띠가 생김

- 칠한 합성 영역의 세로 비율이 상의보다 크게 길면, 상의 밑단 아래 남은 공간이 피부색·검은색 띠로 채워지는 경우가 있음
- 합성 영역을 새 상의 길이에 맞춰 지정하면 피할 수 있음

### 화면에 아직 없는 기능

- 로그인 시간 연장 안내 창, 서버·요청 함수는 준비됨
- 사진첩 결과 삭제: 명세 6-3 미정. 현재는 미저장 결과만 24시간 후 자동 삭제
- 휴대폰의 다듬기 창 브러시와 제외 점 지정
- mock 모드 `VITE_API_MODE=mock`에는 사진 올리기·추출·합성·진행 확인 주소가 없어 합성하기 3단계에서 멈춤. 합성까지 보려면 `mixed`로 실제 서버 사용

---

## 10. 문제 해결 경험

### 1) 합성 한 장에 11~15분

**문제**<br>
작업 관리자에서 GPU 전용 메모리가 가득 차고 공유 GPU 메모리까지 쓰는 것을 확인했습니다.

**해결**<br>
16.8GB 체크포인트를 GPU에서 바로 열던 부분을 시스템 메모리에서 열도록 바꾸고 가중치만 GPU로 옮겼습니다. 이어서 혼합 정밀도와 구성 요소별 GPU 순차 적재를 적용해 약 25초로 줄였습니다. 단계별 수치는 [6장](#6-합성-속도-개선)에 정리했습니다.

### 2) Windows에서 AnyDoor 공식 환경 설치 실패

**문제**<br>
공식 `environment.yaml`은 Linux 전용 패키지를 포함하고, pip 목록의 일부인 `share`, `cmake`, `triton` 등은 Windows에서 받을 수 없었습니다.

**해결**<br>
설치에 실패한 줄의 실제 사용처를 확인해 추론에 필요 없는 항목만 제외하고 설치했습니다.

### 3) 패키지 버전 충돌

**문제**<br>
AnyDoor의 Gradio 데모가 쓰는 gradio 3.39.0은 `numpy<2`가 필요해 서버 환경의 numpy 2.2.6과 충돌했습니다.

**해결**<br>
서버 환경에서는 Gradio를 제외하고, 합성은 `features/composition`에서 AnyDoor 추론 코드만 불러 쓰도록 분리했습니다.

### 4) 새 가상환경에서 torch 설치 실패

**문제**<br>
Python 3.10 기본 pip 23.0.1이 torch 다운로드 주소의 `typing_extensions` 파일을 이름 표기 차이로 거부했습니다.

**해결**<br>
가상환경 안의 pip를 먼저 최신으로 올린 뒤 설치했습니다.

---

## 11. 실행 방법

### 11-1. 백엔드

- 준비 사항
  - Python 가상환경 `CGI`: [environment.md](docs/environment.md)
  - MySQL: [database.md](docs/database.md)
  - GPU, 모델 가중치 파일: 저장소 미포함, AI 기능·서버 담당에게 요청
- 실행 순서: 저장소 최상위 디렉터리
  1. AnyDoor 폴더가 `Desktop\AnyDoor`가 아니면 `$env:ANYDOOR_DIR="AnyDoor 폴더 경로"`
  2. `CGI\Scripts\python.exe -m uvicorn backend.main:app --port 8000`: 서버 실행, 모델 로딩과 예열 약 2분
  3. http://localhost:8000/api/health 접속: `{"status":"ok"}`이면 정상
- API 테스트 페이지: http://localhost:8000/docs
  - 자물쇠 표시가 있는 로그인 필요 API: `POST /api/auth/login` 응답의 `token`을 Authorize 버튼에 입력 후 실행
- 환경 변수: [backend/README.md](backend/README.md) 3. 환경 변수

### 11-2. 프론트엔드

- 준비 사항: Node.js, 11-1 백엔드 실행
- 실행 순서
  1. `cd frontend`: 디렉터리 이동
  2. `npm install`: 의존 패키지 설치, 최초 1회
  3. `frontend/.env.example`을 `frontend/.env.local`로 복사 후 `VITE_API_MODE=mixed`: 백엔드 연결 설정, 최초 1회. 생략하면 모의 데이터로 동작
  4. `npm run dev`: 개발 서버 실행
  5. http://localhost:5173 접속 → 테스트 계정 `test` / `test1234` 로그인

---

## 12. 디렉터리 구성

```
CGI_MOA/
├── README.md                        프로젝트 개요
├── docs/                            공용 문서
│   ├── api.md                       API 명세
│   ├── environment.md               개발 환경 구축
│   ├── pip_freeze.txt               Python 패키지 목록
│   ├── database.md                  MySQL 데이터베이스 구축
│   ├── login_extend.md              로그인 세션 연장 정책
│   └── readme/                      README 그림
├── frontend/                        프론트엔드: React
│   ├── README.md                    프론트엔드 개요
│   └── .env.example                 백엔드 연결 설정 예시
├── backend/                         백엔드: FastAPI
│   ├── README.md                    백엔드 구성
│   └── .env.example                 데이터베이스 접속 설정 예시
├── features/                        AI 모듈: SAM2, AnyDoor
│   ├── object_extraction/README.md  상의 영역 추출 모듈: SAM2
│   └── composition/README.md        이미지 합성 모듈: AnyDoor, 원본 복원, 박스 선 보정
└── scripts/README.md                AI 모듈 단위 테스트, 환경 점검 check_env.py
```

---

## 13. 관련 기술 문서

| 목적 | 참고 문서 |
|---|---|
| 개발 환경 구축 | [environment.md](docs/environment.md), [database.md](docs/database.md) |
| 프론트엔드 개발 | [api.md](docs/api.md), [login_extend.md](docs/login_extend.md), [frontend/README.md](frontend/README.md) |
| API 사양 확인 | [api.md](docs/api.md), [backend/README.md](backend/README.md) |
| 로그인 오류 조치 | [database.md](docs/database.md) 4. 오류별 조치 |
| AI 모듈 단위 테스트 | [scripts/README.md](scripts/README.md) |

---

## 14. 저장소 제외 항목

| 항목 | 내용 | 사유 |
|---|---|---|
| `CGI/` | Python 가상환경 | 개인 환경 |
| `checkpoints/` | 모델 가중치 파일 | 대용량 |
| `storage/` | 업로드 이미지, 합성 결과 | 사용자 데이터 |
| `backend/.env`, `frontend/.env.local` | DB 비밀번호 등 개인 설정 | 보안 |
| VITON-HD | 학습 데이터셋 | 연구용 라이선스 |

---

## 15. 향후 발전 방향

- **합성 품질**: 원본 복원 범위를 합성 영역과 새 상의 영역 안쪽으로 한정, 합성 영역 비율 안내
- **품질 지표 측정**: 특징 보존·자연스러움 30쌍 평가
- **상의 특화 학습**: AI Hub 쉐이프리스 의류 데이터로 AnyDoor 이어 학습 검토
- **화면 기능**: 로그인 시간 연장 안내 창, 휴대폰 다듬기 보정
- **배포**: GPU 서버에 서버·화면 배포

---

<div align="center">

### MOA

**내가 원하는 것, 그게 무엇이든 미리 만나보세요.**<br>
사진 한 장으로 확인하는 새로운 착용 경험

</div>
