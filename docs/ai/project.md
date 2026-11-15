# MOA 프로젝트 정의

AI 도구와 새 팀원이 프로젝트 전체를 파악하기 위한 문서다. 세부 규격은 각 장의 연결 문서를 따른다.

## 1. 개요

| 항목 | 내용 |
|---|---|
| 서비스 | 상의 사진의 의류를 인물 사진에 합성해 시착 이미지를 만드는 웹 서비스 |
| 목적 | 온라인 의류 구매 전 본인 사진 기반 시착 결과 확인, 반품·교환 부담 감소 |
| 과정 | 미래내일 일경험 프로젝트형, 기업 연계 |
| 기간 | 2026.09.28 ~ 2026.11.22 |
| 팀 | CGI 팀 4인 |

## 2. 사용자 흐름

### 2-1. 합성하기

| 단계 | 사용자 동작 | 시스템 처리 |
|---|---|---|
| 1 | 상의 사진 선택·업로드 | 이미지 저장, 최근 사용 이미지 기록 |
| 2 | 인물 사진 선택·업로드 | 이미지 저장, 최근 사용 이미지 기록 |
| 3 | 상의에 포함·제외 점 클릭, 마스크 편집 | SAM2 이미지 분할 |
| 4 | 인물 사진의 합성 영역 클릭, 마스크 편집, 합성 시작 | SAM2 이미지 분할, 합성 작업 대기열 등록 |
| 결과 | 결과 확인, 사진첩 저장, 다운로드 | AnyDoor 이미지 합성, 초해상도, 원본 복원 |

- 내 작업 기록: 지난 결과 선택 시 입력 이미지·마스크로 1~4단계 복원, 재합성
- 저장하지 않은 결과는 24시간 뒤 삭제

### 2-2. 계정

- 회원가입, 로그인, 로그아웃, 로그인 시간 3시간과 만료 전 연장 안내
- 마이페이지: 프로필·이메일·비밀번호 변경, 사진첩, 알림 설정, 고객센터

## 3. 시스템 구성

| 구성 요소 | 기술 | 위치 | 역할 |
|---|---|---|---|
| 웹 화면 | React, Vite, nginx | `frontend/` | 단계별 합성 화면, 마이페이지, API 호출 |
| 웹 서버 | FastAPI | `backend/` | 계정·이미지·작업 API, 합성 작업 대기열, 원본 복원 후처리 |
| DB | MySQL 8, 개발용 SQLite | `backend/db.py` | 회원·세션·이미지·분할 결과·작업·결과 기록 |
| 파일 저장소 | 로컬 폴더 | `storage/` | 업로드 이미지, 마스크, 합성 결과 |
| 모델 추론 서버 | FastAPI, PyTorch, GPU | `model_server/` | SAM2 분할, AnyDoor 합성, Real-ESRGAN 초해상도 |

### 3-1. 배포 구성

- 운영 서버: 웹 화면·웹 서버·MySQL 컨테이너, `deploy/docker-compose.yml`
- GPU 추론 장비: 모델 추론 서버 컨테이너, `model_server/docker-compose.yml`
- 연결: 웹 서버가 `MODEL_SERVER_URL`로 모델 추론 서버에 HTTP 요청, 토큰 인증
- 모델 추론 서버 엔드포인트: `/extract`, `/compose`, `/progress`, `/health`
- 모델 적재 중 요청은 503 응답, 화면은 모델 준비 중 안내 표시

## 4. AI 처리 과정

| 순서 | 처리 | 모델·방식 | 코드 |
|---|---|---|---|
| 1 | 이미지 분할 | SAM 2.1 Hiera Base+, 포함·제외 점 프롬프트, 클릭 지점 포함 영역 유지·내부 구멍 채우기 | `features/object_extraction/` |
| 2 | 상의 경계 보정 | AnyDoor 동봉 iseg 보정 모델, CPU | `features/composition/anydoor_composer.py` |
| 3 | 이미지 합성 | AnyDoor, 합성 영역 둘레 1.3배 정사각 영역 재생성, 50스텝, float16 혼합 정밀도 | `features/composition/anydoor_composer.py` |
| 4 | 초해상도 | Real-ESRGAN x2, 생성 결과 512 → 1024 변환 후 정사각 영역 크기로 축소 | `features/composition/upscale.py` |
| 5 | 원본 복원 | SAM2로 원본 인물·합성 결과 인물·새 상의·원래 상의 분할, 배경은 원본 유지 | `features/composition/restore.py` |

- 상세: [features/composition/README.md](../../features/composition/README.md), [model_server/README.md](../../model_server/README.md)

## 5. 확정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| 합성 모델 | AnyDoor 기반 유지 | 대안 모델 비교에서 상품 형태·무늬 보존 우세, MIT 라이선스 |
| 서비스 가중치 | 추가 학습 가중치 `mix35000_fp16` | 의상 데이터 추가 학습, 검증 손실 감소 |
| 합성 입력 | AnyDoor 기본 입력 형식 `ANYDOOR_INPUT=anydoor` | 재학습 형식 입력 시험의 깨짐 사례 |
| 원본 복원 | 물체 기준 원본 복원 `restore_scene` | 생성 영역 안 배경 원본 유지 비율 향상, 배경 잔상 제거 |
| 초해상도 | Real-ESRGAN x2 적용 | 상의 질감·윤곽 표현 향상 |
| 합성 설정 | 상의 경계 보정 켬, 영역 모양 유지 끔 고정 | 8건 x 4조합 비교: 경계 보정은 결과 동등 이상, 영역 모양 유지는 원래 옷보다 큰 상의에서 깨짐 |
| 배포 | 모델 추론만 GPU 장비 컨테이너, 나머지는 운영 서버 | 운영 서버 GPU 없음 |

## 6. 폴더 지도

```
CGI_MOA/
├── CLAUDE.md               AI 작업 규칙
├── frontend/               React 웹 화면
│   └── src/                pages · studio · mypage · auth · api · styles · utils
├── backend/                FastAPI 웹 서버
│   └── routers/            auth · images · extract · compose · results · files
├── features/               AI 모듈
│   ├── object_extraction/  SAM2 이미지 분할
│   └── composition/        AnyDoor 합성, 초해상도, 원본 복원, 경계 보정
├── model_server/           GPU 모델 추론 서버와 Docker 구성
├── deploy/                 운영 서버 Docker 구성
├── scripts/                단위 테스트, 환경 점검, 데이터 전처리, DB 이전
│   └── retrain/            AnyDoor 추가 학습
└── docs/                   API·DB·환경·Docker 문서, 작업일지
    └── ai/                 AI 작업용 프로젝트 문서
```
