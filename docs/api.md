# MOA API 명세

- 범위: 프론트엔드(`frontend/`)와 백엔드(`backend/`) 간 요청·응답 규격
- 표기: `(미정)` 팀 결정 필요, `(추가 제안)` 기존 명세에 없는 항목으로 팀 합의 필요

## 0. 공통 규칙

### 0-1. 요청 형식

- 경로: 모두 `/api`로 시작
- 메서드: `GET` 조회, `POST` 생성, `PATCH` 일부 수정, `DELETE` 삭제
- 본문: JSON (이미지 전송 시 `multipart/form-data`)
- 인증: 로그인 시 발급받은 토큰을 요청 헤더에 `Authorization: Bearer <토큰>`으로 포함
- 시각: 한국 시간(+09:00), 예 `2026-10-15T18:20:00+09:00`

### 0-2. 오류 응답

- 형식 (프론트엔드는 `message`를 사용자에게 그대로 표시)

```json
{ "error": { "code": "INVALID_IMAGE", "message": "이미지를 읽을 수 없습니다." } }
```

| 상태 코드 | 의미 | `code` 예 |
|---|---|---|
| 400 | 요청 값 오류 | `INVALID_IMAGE`, `INVALID_PASSWORD`, `INVALID_REQUEST` |
| 401 | 인증 필요 (토큰 없음·불일치·만료), 로그인 실패 | `UNAUTHORIZED`, `INVALID_CREDENTIALS` |
| 404 | 대상 없음 (다른 사용자의 데이터 포함) | `RESULT_NOT_FOUND`, `IMAGE_NOT_FOUND` |
| 409 | 중복 | `DUPLICATE_USERNAME` |
| 503 | 일시적 사용 불가 | `DB_UNAVAILABLE` |
| 500 | 서버 내부 오류 | - |

## 1. 페이지별 호출 API

### 1-1. 로그인 팝업

| 사용자 동작 | 호출 API |
|---|---|
| 아이디·비밀번호 입력 후 로그인 | [`POST /api/auth/login`](#2-1-로그인) |
| 회원 정보 입력 후 가입 | [`POST /api/auth/register`](#2-2-회원가입) |

### 1-2. 합성하기 페이지 (`/studio`)

| 사용자 동작 | 호출 API |
|---|---|
| 1·2단계: 상의·인물 이미지 선택 | [`POST /api/images`](#3-1-이미지-업로드) |
| 3단계: 상의 위 좌표 지정 후 확인 | [`POST /api/extract`](#4-1-상의-영역-추출) |
| 4단계: 착용 영역 지정 후 합성 시작 | [`POST /api/compose`](#5-1-합성-요청) |
| 합성 진행 대기 | [`GET /api/jobs/{job_id}`](#5-2-진행-상태-조회) |
| 합성 결과 확인 | [`GET /api/results/{result_id}`](#5-3-결과-조회) |
| 합성 결과 저장 | [`PATCH /api/results/{result_id}`](#6-2-결과-저장-및-좋아요) |
| 내 작업 기록 확인 | [`GET /api/results?saved=true`](#6-1-결과-목록-조회) |

### 1-3. 마이페이지 (`/mypage`)

| 사용자 동작 | 호출 API |
|---|---|
| 사진첩 조회 (분류·날짜·정렬) | [`GET /api/results`](#6-1-결과-목록-조회) |
| 저장, 좋아요 | [`PATCH /api/results/{result_id}`](#6-2-결과-저장-및-좋아요) |
| 프로필 확인 | [`GET /api/me`](#2-3-내-정보-조회) |

### 1-4. 모든 페이지 공통

| 사용자 동작 | 호출 API |
|---|---|
| 로그아웃 | [`POST /api/auth/logout`](#2-4-로그아웃) |
| 로그인 시간 연장 (추가 제안) | [`POST /api/auth/extend`](#2-5-로그인-시간-연장-추가-제안) |

## 2. 계정 관리 API

### 2-1. 로그인

- `POST /api/auth/login`, 인증 불필요
- 요청: `{ "username": "test", "password": "test1234" }`
- 응답: `{ "token": "...", "expires_at": "2026-10-15T18:20:00+09:00", "user": { "id": 1, "username": "test", "name": "MOA User" } }`
  - `expires_at`: 토큰 만료 시각 (추가 제안, 2-5. 로그인 시간 연장)
- 실패: 401 `INVALID_CREDENTIALS`

### 2-2. 회원가입

- `POST /api/auth/register`, 인증 불필요
- 요청: `{ "username", "password", "name", "email" }`
- 응답: 2-1. 로그인과 동일 (가입 즉시 로그인 상태)
- 비밀번호 규칙: 8자 이상, 숫자 포함 (프론트엔드도 전송 전 동일 검사)
- 실패: 400 `INVALID_PASSWORD`(비밀번호 규칙 위반), 409 `DUPLICATE_USERNAME`(아이디 중복)

### 2-3. 내 정보 조회

- `GET /api/me`, 인증 필요
- 응답: `{ "id": 1, "username": "test", "name": "MOA User", "email": "moa.user@example.com", "avatar_url": "/api/files/..." }`

### 2-4. 로그아웃

- `POST /api/auth/logout`, 인증 필요
- 요청 본문 없음, 응답 `{}`
- 백엔드: 해당 토큰 폐기
- 프론트엔드: 응답을 기다리지 않고 로그아웃 처리 (401 응답도 무시)

### 2-5. 로그인 시간 연장 (추가 제안)

- `POST /api/auth/extend`, 인증 필요
- 요청 본문 없음, 응답 `{ "expires_at": "..." }`
- 연장 규칙: [login_extend.md](login_extend.md)

## 3. 이미지 업로드 API

### 3-1. 이미지 업로드

- `POST /api/images`, 인증 필요, `multipart/form-data`
- 요청: `file`(jpg, png), `kind`(`"garment"` 상의 / `"person"` 인물)
- 응답: `{ "image_id": "img_123", "url": "/api/files/img_123.jpg", "width": 768, "height": 1024 }`
- 업로드 시점: 합성하기 1·2단계에서 이미지 선택 시 (예시 이미지 포함)
- 이후 추출·합성 요청은 `image_id`로 이미지 지정
- 제한: 10MB 이하, jpg·png (위반 시 400 `IMAGE_TOO_LARGE`, `INVALID_IMAGE`)
- 긴 변 길이 제한 (미정, 제안 4096px)

## 4. 상의 영역 추출 API (SAM2)

### 4-1. 상의 영역 추출

- `POST /api/extract`, 인증 필요
- 요청

```json
{ "image_id": "img_123", "points": [ { "x": 0.52, "y": 0.41, "label": 1 }, { "x": 0.70, "y": 0.20, "label": 0 } ] }
```

| 필드 | 내용 |
|---|---|
| `x`, `y` | 이미지 내 위치, 0~1 비율 (왼쪽 위 0,0) |
| `label` | 1 포함 (왼쪽 클릭), 0 제외 (오른쪽 클릭) |
| `box` | 상의를 감싸는 사각형 `{ "x1", "y1", "x2", "y2" }` 0~1 비율, 선택 (추가 제안) |

- 응답

```json
{ "extraction_id": "ext_456", "mask_url": "/api/files/ext_456_mask.png", "cutout_url": "/api/files/ext_456_cutout.png", "bbox": { "x": 120, "y": 200, "w": 400, "h": 520 } }
```

| 필드 | 내용 |
|---|---|
| `mask_url` | 원본 크기 흑백 PNG (상의 영역 255) |
| `cutout_url` | 상의 영역만 남긴 투명 배경 PNG |
| `bbox` | 상의 영역 경계 사각형 (원본 픽셀 기준) |

- 호출 시점: 좌표 지정 후 "확인" 시 1회 (좌표 지정 중에는 호출하지 않음)
- 프론트엔드: 추출 결과 표시 후 "이대로 진행 / 점 다시 찍기" 선택
- 재지정 시 재호출, 마지막 `extraction_id`를 5-1. 합성 요청에 사용

## 5. 이미지 합성 API (AnyDoor)

- 처리 방식: 합성 요청 → 작업 번호 수신 → 2초 간격 진행 상태 조회 → 결과 조회
- 설정: 50스텝, 1건 약 1분

### 5-1. 합성 요청

- `POST /api/compose`, 인증 필요, `multipart/form-data`
- 요청

| 필드 | 내용 |
|---|---|
| `extraction_id` | 4-1. 상의 영역 추출 결과 번호 |
| `person_image_id` | 3-1. 이미지 업로드의 인물 이미지 번호 |
| `area_mask` | 착용 영역 흑백 PNG (지정 영역 255), 인물 이미지와 같은 비율 |

- 응답: `{ "job_id": "job_789", "status": "queued", "queue_position": 1 }`
- 스텝 수·시드: 백엔드에서 결정

### 5-2. 진행 상태 조회

- `GET /api/jobs/{job_id}`, 인증 필요
- 응답: `{ "job_id": "job_789", "status": "running", "progress": 0.34, "queue_position": 0, "result_id": null, "error": null }`

| 필드 | 내용 |
|---|---|
| `status` | `queued` 대기, `running` 합성 중, `done` 완료, `failed` 실패 |
| `progress` | 진행률 0~1 |
| `queue_position` | 대기 순번 (0: 대기 없음) |

- 프론트엔드: 2초 간격 조회, `done`이면 5-3. 결과 조회
- 프론트엔드: 새로고침 후에도 조회를 이어 가도록 `job_id`를 브라우저에 저장

### 5-3. 결과 조회

- `GET /api/results/{result_id}`, 인증 필요
- 응답

```json
{ "result_id": "res_001", "image_url": "/api/files/res_001.png", "thumb_url": "/api/files/res_001_thumb.jpg", "created_at": "2026-10-12T20:45:00+09:00", "saved": false, "favorite": false, "garment_image_id": "img_123", "person_image_id": "img_124" }
```

- 합성 결과는 "최근 작업"(`saved: false`)으로 생성, 저장 시 사진첩(`saved: true`)으로 이동
- 저장하지 않은 결과: 생성 3일 후 자동 삭제

## 6. 합성 결과 관리 API (작업 기록, 사진첩)

### 6-1. 결과 목록 조회

- `GET /api/results`, 인증 필요
- 조건 (모두 선택)

| 조건 | 내용 |
|---|---|
| `saved=true` / `false` | 사진첩 "전체" / "최근 작업" |
| `favorite=true` | "좋아요" |
| `date=2026-10-12` | 해당 날짜 생성분 (한국 시간 기준) |
| `sort=new` / `old` | 최신순 (기본) / 오래된순 |
| `limit`, `cursor` | 분할 조회 (미정) |

- 응답

```json
{ "items": [ { "result_id": "res_001", "thumb_url": "...", "image_url": "...", "created_at": "...", "saved": true, "favorite": true } ], "counts": { "saved": 20, "recent": 6, "favorite": 6 }, "next_cursor": null }
```

- `counts`: 분류별 개수 (사진첩 탭 표시)
- 내 작업 기록: `saved=true`, 최신순

### 6-2. 결과 저장 및 좋아요

- `PATCH /api/results/{result_id}`, 인증 필요
- 요청: `{ "saved": true }` 또는 `{ "favorite": true }`
- 응답: 5-3. 결과 조회와 동일

### 6-3. 결과 삭제 (미정)

- `DELETE /api/results/{result_id}`

## 7. 이미지 파일 조회 API

- `GET /api/files/{파일 이름}`: 위 응답의 `url`, `image_url`, `mask_url` 등
- 요구 사항: 본인 파일만 조회 가능
- 제약: `<img src>` 요청에는 `Authorization` 헤더 포함 불가
- 접근 제어 방식 (미정)
  1. 일정 시간만 유효한 주소 `?key=...` 발급 (제안)
  2. 쿠키 기반 로그인
  3. 프론트엔드가 토큰을 포함해 직접 내려받기 (이미지가 많으면 느림)

## 8. 팀 결정 사항

### 8-1. 확정 사항

| 항목 | 내용 | 관련 절 |
|---|---|---|
| 추출 호출 시점 | "확인" 시 1회, "이대로 진행 / 점 다시 찍기" | [4-1. 상의 영역 추출](#4-1-상의-영역-추출) |
| 합성 설정 | 50스텝, 1건 1분 내외 | [5. 이미지 합성 API (AnyDoor)](#5-이미지-합성-api-anydoor) |
| 진행 상태 조회 | 2초 간격, 진행률 제공 | [5-2. 진행 상태 조회](#5-2-진행-상태-조회) |
| 미저장 결과 보관 | 3일 | [5-3. 결과 조회](#5-3-결과-조회) |
| 이미지 제한 | 10MB 이하, jpg·png | [3-1. 이미지 업로드](#3-1-이미지-업로드) |
| 비밀번호 규칙 | 8자 이상, 숫자 포함 | [2-2. 회원가입](#2-2-회원가입) |
| 로그아웃 | 백엔드에 통보 | [2-4. 로그아웃](#2-4-로그아웃) |
| 날짜 기준 | 한국 시간 | [6-1. 결과 목록 조회](#6-1-결과-목록-조회) |
| 개발 서버 주소 | `http://localhost:8000` | - |
| 로그인 유효 시간 | 3시간, 만료 30분·10분 전 연장 확인 | [2-5. 로그인 시간 연장](#2-5-로그인-시간-연장-추가-제안) |

### 8-2. 미정 사항

1. 파일 접근 제어 방식: [7. 이미지 파일 조회 API](#7-이미지-파일-조회-api)
2. 이미지 긴 변 길이 제한: [3-1. 이미지 업로드](#3-1-이미지-업로드)
3. 결과 목록 분할 조회: [6-1. 결과 목록 조회](#6-1-결과-목록-조회)
4. 결과 삭제: [6-3. 결과 삭제](#6-3-결과-삭제-미정)
5. 추가 제안 채택: [2-5. 로그인 시간 연장](#2-5-로그인-시간-연장-추가-제안), [4-1. 상의 영역 추출](#4-1-상의-영역-추출)의 `box`
