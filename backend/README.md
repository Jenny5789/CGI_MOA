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
| `storage.py` | 저장 기록 읽기, 소유자 확인 | - |
| `gpu.py` | GPU 작업 순서 제어 | - |

## 3. 구현 방식

| 항목 | 방식 |
|---|---|
| 회원·로그인 세션 | MySQL `users`, `sessions` 테이블 ([database.md](../docs/database.md)), 토큰은 해시로만 저장 |
| 이미지·추출·합성 결과 | `storage/` 폴더에 파일과 기록(JSON)으로 저장 (데이터베이스 미사용) |
| 데이터 소유 | 기록마다 회원 번호 저장, 다른 회원의 기록 요청 시 404 |
| GPU 사용 | 추출·합성을 한 번에 1건씩 처리 (합성 중 추출 요청은 대기) |
| 합성 작업 상태 | 메모리에 보관, 서버 재시작 시 진행 중이던 작업은 실패(`SERVER_RESTARTED`) |
| 미저장 결과 삭제 | 생성 3일 경과분을 결과 목록 조회 시 삭제 |
| AnyDoor 예열 | 서버 시작 시 모델 로딩 1~2분, 환경 변수 `MOA_WARMUP=0`이면 생략 |
| 데이터베이스 연결 실패 | 서버는 실행, 로그인이 필요한 모든 API는 503 `DB_UNAVAILABLE` |
| 이미지 파일 조회 | 인증 없음 (접근 제어 방식 미정, [8. 미정 사항](../docs/api.md#8-미정-사항)) |
