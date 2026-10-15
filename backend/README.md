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
