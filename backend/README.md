# 백엔드 (FastAPI)

## 1. 개요

- 역할: 프론트엔드 요청 처리 (로그인, 이미지 업로드, 상의 영역 추출 SAM2, 이미지 합성 AnyDoor, 합성 결과 관리)
- API 명세: [docs/api.md](../docs/api.md)
- 실행 방법: [README.md 5-1. 백엔드](../README.md#5-1-백엔드)

## 2. 파일 구성

| 파일 | 기능 | 관련 명세 |
|---|---|---|
| `main.py` | 서버 시작, API 등록, AnyDoor 예열 | - |
| `config.py` | 저장 위치, 업로드 제한 값, 프로필 사진 크기 | - |
| `errors.py` | 오류 응답 형식 | [0. 공통 규칙](../docs/api.md#0-공통-규칙) |
| `db.py` | MySQL 연결, 테이블·테스트 계정 생성, 예전 표에 새 칸 추가 | - |
| `auth.py`, `routers/auth.py` | 로그인, 회원가입, 내 정보, 로그아웃, 로그인 시간 연장, 마이페이지 계정 설정 | [2. 계정 관리 API](../docs/api.md#2-계정-관리-api) |
| `routers/images.py` | 이미지 업로드 | [3-1. 이미지 업로드](../docs/api.md#3-1-이미지-업로드) |
| `routers/extract.py` | 상의 영역 추출 (SAM2) | [4-1. 상의 영역 추출](../docs/api.md#4-1-상의-영역-추출) |
| `routers/compose.py` | 합성 요청, 진행 상태 조회 (AnyDoor) | [5. 이미지 합성 API](../docs/api.md#5-이미지-합성-api-anydoor) |
| `routers/results.py` | 결과 조회, 목록, 저장·좋아요 | [6. 합성 결과 관리 API](../docs/api.md#6-합성-결과-관리-api-작업-기록-사진첩) |
| `routers/files.py` | 이미지 파일 조회 | [7. 이미지 파일 조회 API](../docs/api.md#7-이미지-파일-조회-api) |
| `file_keys.py` | 이미지 파일 주소 열쇠 발급·확인 (3시간 유효) | [7. 이미지 파일 조회 API](../docs/api.md#7-이미지-파일-조회-api) |
| `storage.py` | 저장 기록 읽기, 소유자 확인 | - |
| `gpu.py` | GPU 작업 순서 제어 | - |

## 3. 환경 변수

| 이름 | 용도 | 기본값 | 설정 위치 |
|---|---|---|---|
| `DATABASE_URL` | MySQL 접속 정보 | 없음 (필수) | `backend/.env` ([database.md 2-3. 접속 설정 파일 생성](../docs/database.md#2-3-접속-설정-파일-생성)) |
| `ANYDOOR_DIR` | AnyDoor 폴더 위치 | `Desktop\AnyDoor` | 실행 전 PowerShell `$env:ANYDOOR_DIR="경로"` |
| `MOA_WARMUP` | `0`이면 서버 시작 시 AnyDoor 모델 로딩(1~2분) 생략 | `1` (로딩함) | 실행 전 PowerShell `$env:MOA_WARMUP="0"` |
| `MOA_SEAM_FIX` | `0`이면 합성 후 박스 선 보정 생략 ([features/composition/README.md](../features/composition/README.md#박스-선-보정-seampy)) | `1` (보정함) | 실행 전 PowerShell `$env:MOA_SEAM_FIX="0"` |

- SAM2 관련 설정: [features/object_extraction/README.md](../features/object_extraction/README.md)

## 4. 마이페이지 계정 설정 · 2026-10-20

| 주소 | 기능 | 명세 |
|---|---|---|
| `PATCH /api/me` | 이름 1~20자, 휴대폰 번호, 소개 글 60자 이하. 보낸 항목만 변경 | [2-7](../docs/api.md#2-7-프로필-수정-추가-제안) |
| `POST /api/me/avatar`, `DELETE /api/me/avatar` | 프로필 사진 올리기, 기본 그림으로 | [2-8](../docs/api.md#2-8-프로필-사진-변경-추가-제안) |
| `PATCH /api/me/email` | 이메일 변경, 지금 비밀번호 확인 | [2-9](../docs/api.md#2-9-이메일-변경-추가-제안) |
| `PATCH /api/me/password` | 비밀번호 변경, 이 토큰만 남기고 같은 회원의 다른 토큰 폐기 | [2-10](../docs/api.md#2-10-비밀번호-변경-추가-제안) |

- DB: 서버 시작 시 `users` 표에 `bio` 소개 글, `avatar` 프로필 사진 파일명 칸이 없으면 추가. 기존 데이터 유지
- 프로필 사진: 사진 업로드와 동일한 jpg·png, 10MB 이하 검사 → 휴대폰 회전 정보 반영 → 중앙 정사각형 256px로 `storage/avatars/avt_xxx.jpg` 저장. EXIF 미저장. 변경마다 새 파일명 부여로 브라우저 캐시의 이전 사진 표시 방지
- 프로필 사진 주소: 다른 사진과 동일하게 `?key=` 열쇠가 붙은 `/api/files/avt_...` 주소. `config.py` `FILE_DIRS`의 `avt`
- 시험: `MOA_WARMUP=0` 설정의 8001 포트 별도 서버에서 22개 사례 확인. 형식 오류 400, 비밀번호 불일치 400, 중복 이메일 409, 비밀번호 변경 후 타 기기 토큰 401, 사진 256×256·EXIF 없음
