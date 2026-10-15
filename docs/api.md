# MOA API 명세

- 기준: 화면(`frontend/`)이 서버에 보내고 받는 값
- `(미정)`: 팀 결정 필요 / `(추가 제안)`: 명세 외 추가, 팀 합의 필요

## 0. 공통

- 주소: 모두 `/api`로 시작
- 방식: `GET` 가져오기 / `POST` 만들기 / `PATCH` 일부 고치기 / `DELETE` 지우기
- 값: JSON. 사진은 파일 첨부(`multipart/form-data`)
- 로그인 필요: 요청 머리에 `Authorization: Bearer <토큰>`
- 오류: 상태 번호 + 아래 형식, 화면은 `message`를 그대로 표시

```json
{ "error": { "code": "INVALID_IMAGE", "message": "이미지를 읽을 수 없습니다." } }
```

| 번호 | 뜻 | 예 |
|---|---|---|
| 400 | 보낸 값 잘못됨 | 사진 형식, 비밀번호 규칙, 필수 값 빠짐 |
| 401 | 로그인 필요(토큰 없음·틀림·만료) 또는 로그인 실패 | `UNAUTHORIZED` → 로그인 창, `INVALID_CREDENTIALS` |
| 404 | 없음 (남의 것도 404) | `RESULT_NOT_FOUND`, `IMAGE_NOT_FOUND` |
| 409 | 이미 있음 | `DUPLICATE_USERNAME` |
| 503 | 지금 쓸 수 없음 | `DB_UNAVAILABLE` |
| 500 | 서버 내부 오류 | |

## 1. 화면과 API

| 화면 | 하는 일 | API |
|---|---|---|
| 로그인 팝업 | 아이디, 비밀번호 | 2-1 |
| 회원가입 | (화면은 "준비 중") | 2-2 |
| 합성하기 1·2단계 | 상의·인물 사진 고르기 | 3-1 |
| 합성하기 3단계 | 상의에 점 찍기 → 확인 | 4-1 |
| 합성하기 4단계 | 입힐 영역 칠하기 → 합성 시작 | 5-1 |
| 합성 중 | 기다리기 | 5-2 |
| 결과 | 보기, 저장 | 5-3, 6-2 |
| 내 작업 기록 | 저장한 결과 | 6-1 |
| 마이페이지 사진첩 | 탭, 날짜, 정렬, 저장, 좋아요 | 6-1, 6-2 |
| 마이페이지 프로필 | 이름, 이메일, 사진 | 2-3 |

## 2. 계정

### 2-1. 로그인
`POST /api/auth/login`

- 보내는 값: `{ "username": "test", "password": "test1234" }`
- 받는 값: `{ "token": "...", "expires_at": "2026-10-15T18:20:00+09:00", "user": { "id": 1, "username": "test", "name": "MOA User" } }`
  - `expires_at`: 토큰 만료 시각 (추가 제안, 2-5)
- 틀리면 401 `INVALID_CREDENTIALS` "아이디 또는 비밀번호가 올바르지 않습니다"

### 2-2. 회원가입
`POST /api/auth/register`

- 보내는 값: `{ "username", "password", "name", "email" }`
- 받는 값: 2-1과 같음 (가입 후 바로 로그인)
- 아이디 중복: 409 `DUPLICATE_USERNAME`
- 비밀번호 규칙: 8자 이상, 숫자 포함. 어기면 400 `INVALID_PASSWORD` (화면도 보내기 전 같은 검사)

### 2-3. 내 정보
`GET /api/me`, 로그인 필요

- 받는 값: `{ "id": 1, "username": "test", "name": "MOA User", "email": "moa.user@example.com", "avatar_url": "/api/files/..." }`

### 2-4. 로그아웃
`POST /api/auth/logout`, 로그인 필요

- 보내는 값 없음, 받는 값 `{}`
- 서버: 이 토큰 폐기
- 화면: 응답을 기다리지 않고 로그아웃, 401이 와도 무시

### 2-5. 로그인 시간 연장 (추가 제안)
`POST /api/auth/extend`, 로그인 필요

- 보내는 값 없음, 받는 값 `{ "expires_at": "..." }`
- 규칙: [login_extend.md](login_extend.md)

## 3. 사진

### 3-1. 사진 올리기
`POST /api/images`, 로그인 필요, 파일 첨부

- 보내는 값: `file` (jpg, png), `kind`: `"garment"` 또는 `"person"`
- 받는 값: `{ "image_id": "img_123", "url": "/api/files/img_123.jpg", "width": 768, "height": 1024 }`
- 화면: 1·2단계에서 사진을 고를 때 올림 (예시 사진도)
- 추출·합성은 `image_id`로 요청
- 제한: 10MB 이하, jpg/png. 넘으면 400 `IMAGE_TOO_LARGE` / `INVALID_IMAGE`
- 긴 변 길이 제한 (미정, 제안 4096)

## 4. 상의 추출

### 4-1. 상의 추출
`POST /api/extract`, 로그인 필요

- 보내는 값
  ```json
  { "image_id": "img_123", "points": [ { "x": 0.52, "y": 0.41, "label": 1 }, { "x": 0.70, "y": 0.20, "label": 0 } ] }
  ```
  - `x`, `y`: 0~1 비율 (왼쪽 위 0,0)
  - `label`: 1 포함(왼쪽 클릭), 0 제외(오른쪽 클릭)
  - `box`: `{ "x1", "y1", "x2", "y2" }` 0~1 비율, 선택 (추가 제안). 점만 / 박스만 / 박스 + 점
- 받는 값
  ```json
  { "extraction_id": "ext_456", "mask_url": "/api/files/ext_456_mask.png", "cutout_url": "/api/files/ext_456_cutout.png", "bbox": { "x": 120, "y": 200, "w": 400, "h": 520 } }
  ```
  - `mask_url`: 원본 크기 흑백 PNG (상의 255)
  - `cutout_url`: 상의만 남긴 투명 배경 PNG
  - `bbox`: 상의 사각형 (원본 픽셀)
- 확인을 누를 때 한 번만 호출 (점 찍는 동안은 안 부름)
- 화면: 결과를 보여 주고 "이대로 진행 / 점 다시 찍기"
- 다시 찍고 확인하면 다시 호출 → 새 `extraction_id`. 마지막 것을 5-1에 사용

## 5. 합성

- 방식: 요청 → 작업 번호 받기 → 2초마다 진행 확인 → 결과 받기
- 설정: 50스텝, 1장 약 1분

### 5-1. 합성 요청
`POST /api/compose`, 로그인 필요, 파일 첨부

- 보내는 값
  - `extraction_id`: 4-1 번호
  - `person_image_id`: 3-1 인물 사진 번호
  - `area_mask`: 입힐 영역 흑백 PNG (칠한 곳 255), 인물 사진과 같은 비율
- 받는 값: `{ "job_id": "job_789", "status": "queued", "queue_position": 1 }`
- 스텝·시드는 서버가 정함

### 5-2. 진행 확인
`GET /api/jobs/{job_id}`, 로그인 필요

- 받는 값: `{ "job_id": "job_789", "status": "running", "progress": 0.34, "queue_position": 0, "result_id": null, "error": null }`
- `status`: `queued` / `running` / `done` / `failed`
- `progress`: 0~1
- 화면: 2초마다 호출, `done`이면 5-3
- 화면: 새로고침해도 이어서 확인하도록 `job_id`를 브라우저에 저장

### 5-3. 결과 받기
`GET /api/results/{result_id}`, 로그인 필요

- 받는 값
  ```json
  { "result_id": "res_001", "image_url": "/api/files/res_001.png", "thumb_url": "/api/files/res_001_thumb.jpg", "created_at": "2026-10-12T20:45:00+09:00", "saved": false, "favorite": false, "garment_image_id": "img_123", "person_image_id": "img_124" }
  ```
- 합성 결과는 "최근 작업"(`saved: false`), "저장"하면 사진첩(`saved: true`)
- 저장 안 한 결과는 3일 뒤 삭제

## 6. 작업 기록과 사진첩

### 6-1. 결과 목록
`GET /api/results`, 로그인 필요

- 조건 (모두 선택)
  - `saved=true|false`: "전체" / "최근 작업"
  - `favorite=true`: "좋아요"
  - `date=2026-10-12`: 그날 만든 것 (한국 시간)
  - `sort=new|old`: 기본 `new`
  - `limit`, `cursor`: 나눠 받기 (미정)
- 받는 값
  ```json
  { "items": [ { "result_id": "res_001", "thumb_url": "...", "image_url": "...", "created_at": "...", "saved": true, "favorite": true } ], "counts": { "saved": 20, "recent": 6, "favorite": 6 }, "next_cursor": null }
  ```
  - `counts`: 탭 옆 숫자
- 내 작업 기록: `saved=true`, 최신순

### 6-2. 저장 / 좋아요
`PATCH /api/results/{result_id}`, 로그인 필요

- 보내는 값: `{ "saved": true }` 또는 `{ "favorite": true }`
- 받는 값: 5-3과 같음

### 6-3. 결과 지우기 (미정)
`DELETE /api/results/{result_id}`

## 7. 파일

`GET /api/files/{파일 이름}`: 위 응답의 `url`

- 본인 것만 보여야 함
- 문제: `<img src>`는 `Authorization` 머리를 못 붙임
- 확인 방식 (미정)
  - (가) 일정 시간만 열리는 주소 `?key=...` (제안)
  - (나) 쿠키 로그인
  - (다) 화면이 토큰을 붙여 직접 받기 (사진 많으면 느림)

## 8. 결정 사항

### 확정

| 항목 | 내용 | 명세 위치 |
|---|---|---|
| 추출 호출 | 확인 때 한 번, "이대로 진행 / 점 다시 찍기" | 4-1 |
| 합성 | 50스텝, 1분 안팎 | 5장 |
| 진행 확인 | 2초마다, 진행률 제공 | 5-2 |
| 저장 안 한 결과 | 3일 보관 | 5-3 |
| 사진 | 10MB 이하, jpg/png | 3-1 |
| 비밀번호 | 8자 이상, 숫자 포함 | 2-2 |
| 로그아웃 | 서버에도 알림 | 2-4 |
| 날짜 기준 | 한국 시간 | 6-1 |
| 서버 주소 (개발) | `http://localhost:8000` | - |
| 로그인 유효 | 3시간, 만료 30분·10분 전 연장 확인 | 2-5 |

### 미정

1. `/api/files` 본인 확인 방식 (7장)
2. 사진 긴 변 길이 제한 (3-1)
3. 결과 목록 나눠 받기 (6-1)
4. 결과 지우기 (6-3)
5. 추가 제안 채택 여부: 로그인 연장(2-5), 추출 `box`(4-1)
