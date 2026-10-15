# 백엔드 (FastAPI)

## 1. 개요

- 역할: 프론트엔드 요청 처리 (로그인, 이미지 업로드, 상의 영역 추출 SAM2, 이미지 합성 AnyDoor, 합성 결과 관리)
- API 명세: [docs/api.md](../docs/api.md)
- 실행 방법: [README.md 5-1. 백엔드](../README.md#5-1-백엔드)

## 2. 파일 구성

| 파일 | 기능 | 관련 명세 |
|---|---|---|
| `main.py` | 서버 시작, API 등록, AnyDoor 예열 | - |
| `config.py` | 저장 위치, 업로드 제한 값 | - |
| `errors.py` | 오류 응답 형식 | [0. 공통 규칙](../docs/api.md#0-공통-규칙) |
| `db.py` | MySQL 연결, 테이블·테스트 계정 생성 | - |
| `auth.py`, `routers/auth.py` | 로그인, 회원가입, 내 정보, 로그아웃, 로그인 시간 연장 | [2. 계정 관리 API](../docs/api.md#2-계정-관리-api) |
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

- SAM2 관련 설정: [features/object_extraction/README.md](../features/object_extraction/README.md)
