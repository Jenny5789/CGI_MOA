# MOA API 명세

- 범위: 프론트엔드(`frontend/`)와 백엔드(`backend/`) 간 요청·응답 규격
- 표기: `(미정)` 팀 결정 필요, `(추가 제안)` 기존 명세에 없는 항목으로 팀 합의 필요

## 0. 공통 규칙

### 0-1. 요청 형식

- 서버 주소 (개발): `http://localhost:8000`
- 경로: 모두 `/api`로 시작
- 메서드: `GET` 조회, `POST` 생성, `PATCH` 일부 수정, `DELETE` 삭제
- 본문: JSON (이미지 전송 시 `multipart/form-data`)
- 인증: 로그인 시 발급받은 토큰을 요청 헤더에 `Authorization: Bearer <토큰>`으로 포함
- 시각: 한국 시간(+09:00), 예 `2026-10-15T18:20:00+09:00`
- 필드 표의 필수 칸: `O` 필수, `-` 선택, `조건` 표 아래 조건 참고

### 0-2. 오류 응답

- 형식 (프론트엔드는 `message`를 사용자에게 그대로 표시)

```json
{
  "error": {
    "code": "INVALID_IMAGE",
    "message": "이미지를 읽을 수 없습니다."
  }
}
```

| 상태 코드 | 의미 |
|---|---|
| 400 | 요청 값 오류 |
| 401 | 인증 필요 (토큰 없음·불일치·만료), 로그인 실패 |
| 404 | 대상 없음 (다른 사용자의 데이터 포함) |
| 409 | 중복 |
| 503 | 일시적 사용 불가 |
| 500 | 서버 내부 오류 (오류 형식이 아닌 일반 응답일 수 있음) |

- 공통 오류 (모든 API에서 발생 가능, 각 절의 오류 표에는 생략)

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_REQUEST` | 필수 값 누락, 형식 오류 |
| 401 | `UNAUTHORIZED` | 인증 필요 API에서 토큰 없음·불일치·만료 (프론트엔드는 로그인 창 표시) |
| 503 | `DB_UNAVAILABLE` | 로그인·회원가입, 인증 필요 API에서 데이터베이스 연결 불가 |

## 1. 페이지별 호출 API

### 1-1. 로그인 팝업

| 구분 | 사용자 동작 | 호출 API | 상세 설명 |
|---|---|---|---|
| 로그인 | 아이디·비밀번호 입력 후 로그인 | `POST /api/auth/login` | [2-1. 로그인](#2-1-로그인) |
| 회원가입 | 회원 정보 입력 후 가입 | `POST /api/auth/register` | [2-2. 회원가입](#2-2-회원가입) |
| 아이디 중복확인 | 회원가입 창에서 중복확인 버튼 | `GET /api/auth/check-username` | [2-6. 아이디 중복확인](#2-6-아이디-중복확인) |

### 1-2. 합성하기 페이지 (`/studio`)

| 구분 | 사용자 동작 | 호출 API | 상세 설명 |
|---|---|---|---|
| 1·2단계 | 상의·인물 이미지 선택 | `POST /api/images` | [3-1. 이미지 업로드](#3-1-이미지-업로드) |
| 1·2단계 | 더보기 창의 최근 사용한 사진 | `GET /api/images/recent` | [3-2. 최근 사용한 이미지](#3-2-최근-사용한-이미지) |
| 3단계 | 상의 위 좌표 지정 후 확인 | `POST /api/extract` | [4-1. 상의 영역 추출](#4-1-상의-영역-추출) |
| 4단계 | 착용 영역 지정 후 합성 시작 | `POST /api/compose` | [5-1. 합성 요청](#5-1-합성-요청) |
| 합성 중 화면 | 진행 상태 확인 (2초 간격 자동) | `GET /api/jobs/{job_id}` | [5-2. 진행 상태 조회](#5-2-진행-상태-조회) |
| 결과 화면 | 합성 결과 확인 | `GET /api/results/{result_id}` | [5-3. 결과 조회](#5-3-결과-조회) |
| 결과 화면 | 합성 결과 저장 | `PATCH /api/results/{result_id}` | [6-2. 결과 저장 및 좋아요](#6-2-결과-저장-및-좋아요) |
| 오른쪽 패널 | 내 작업 기록 확인 (저장 여부 무관) | `GET /api/results` | [6-1. 결과 목록 조회](#6-1-결과-목록-조회) |
| 오른쪽 패널 (추가 제안) | 작업 기록을 열면 1~4단계 채우기 | `GET /api/results/{result_id}/source` | [6-4. 결과 재료 조회](#6-4-결과-재료-조회-추가-제안) |

### 1-3. 마이페이지 (`/mypage`)

| 구분 | 사용자 동작 | 호출 API | 상세 설명 |
|---|---|---|---|
| 사진첩 | 저장한 결과 조회 (분류·날짜·정렬) | `GET /api/results?saved=true` | [6-1. 결과 목록 조회](#6-1-결과-목록-조회) |
| 사진첩 | 저장, 좋아요 | `PATCH /api/results/{result_id}` | [6-2. 결과 저장 및 좋아요](#6-2-결과-저장-및-좋아요) |
| 프로필 | 이름, 이메일, 프로필 이미지 확인 | `GET /api/me` | [2-3. 내 정보 조회](#2-3-내-정보-조회) |
| 사진첩 ⋯ 메뉴 | 크게 보기, 다운로드 | 없음. 결과의 `image_url` 사용 | [6-1. 결과 목록 조회](#6-1-결과-목록-조회) |
| 계정 설정 (추가 제안) | 이름·휴대폰 번호·소개 글 수정 | `PATCH /api/me` | [2-7. 프로필 수정](#2-7-프로필-수정-추가-제안) |
| 계정 설정 (추가 제안) | 프로필 사진 변경, 기본 그림으로 | `POST`·`DELETE /api/me/avatar` | [2-8. 프로필 사진 변경](#2-8-프로필-사진-변경-추가-제안) |
| 계정 설정 (추가 제안) | 이메일 변경 | `PATCH /api/me/email` | [2-9. 이메일 변경](#2-9-이메일-변경-추가-제안) |
| 계정 설정 (추가 제안) | 비밀번호 변경 | `PATCH /api/me/password` | [2-10. 비밀번호 변경](#2-10-비밀번호-변경-추가-제안) |
| 설정 | 합성 완료 알림, 합성 기본 설정 | 없음. 브라우저 저장 | - |

### 1-4. 모든 페이지 공통

| 구분 | 사용자 동작 | 호출 API | 상세 설명 |
|---|---|---|---|
| 상단 메뉴 | 로그아웃 | `POST /api/auth/logout` | [2-4. 로그아웃](#2-4-로그아웃) |
| 연장 안내 창 (추가 제안) | 로그인 시간 연장 | `POST /api/auth/extend` | [2-5. 로그인 시간 연장](#2-5-로그인-시간-연장-추가-제안) |

## 2. 계정 관리 API

### 2-1. 로그인

- 개요: 아이디·비밀번호 확인 후 인증 토큰 발급
- 요청: `POST /api/auth/login`, 인증 불필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `username` | `string` | O | 아이디 |
| `password` | `string` | O | 비밀번호 |

- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `token` | `string` | 인증 토큰 (이후 요청 헤더에 사용) |
| `expires_at` | `string` (시각) | 토큰 만료 시각 (추가 제안) |
| `user` | `object` | `id`(번호), `username`(아이디), `name`(이름) |

```json
{
  "token": "...",
  "expires_at": "2026-10-15T18:20:00+09:00",
  "user": {
    "id": 1,
    "username": "test",
    "name": "MOA User"
  }
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 401 | `INVALID_CREDENTIALS` | 아이디 없음 또는 비밀번호 불일치 (구분하지 않음) |

- 비고: 토큰 유효 시간 3시간 (로그인 시각 기준)

### 2-2. 회원가입

- 개요: 회원 등록 후 즉시 로그인 상태로 토큰 발급
- 요청: `POST /api/auth/register`, 인증 불필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `username` | `string` | O | 아이디 (공백 없이 12자 이하) |
| `password` | `string` | O | 비밀번호 (8자 이상, 숫자 1개 이상 포함) |
| `email` | `string` | O | 이메일 (형식 검사, 소문자로 저장, 한 이메일로 1회만 가입) |
| `phone` | `string` | - | 휴대폰 번호 (`010-1234-5678`, 하이픈 생략 가능, `010-1234-5678` 형식으로 저장) |
| `name` | `string` | - | 이름 (생략 시 아이디로 저장) |

- 응답 (200): 2-1. 로그인과 동일
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_USERNAME` | 아이디 공백 포함 또는 12자 초과 |
| 400 | `INVALID_PASSWORD` | 비밀번호 규칙 위반 |
| 400 | `INVALID_EMAIL` | 이메일 누락 또는 형식 오류 |
| 400 | `INVALID_PHONE` | 전화번호 입력 시 휴대폰 번호 형식 오류 |
| 409 | `DUPLICATE_USERNAME` | 이미 사용 중인 아이디 |
| 409 | `DUPLICATE_EMAIL` | 이미 가입된 이메일 (대소문자 구분 없음) |

- 비고: 프론트엔드도 전송 전 같은 규칙으로 검사 (`frontend/src/auth/signupRules.js`), 비밀번호 확인 칸은 프론트엔드에서만 비교
- 비고: 이메일 인증 메일은 보내지 않음 (형식 검사와 중복 가입 금지로 무분별한 가입 방지)

### 2-3. 내 정보 조회

- 개요: 로그인한 사용자의 프로필 정보 조회
- 요청: `GET /api/me`, 인증 필요
- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `id` | `integer` | 회원 번호 |
| `username` | `string` | 아이디 |
| `name` | `string` | 이름 |
| `email` | `string` \| `null` | 이메일 |
| `phone` | `string` \| `null` | 휴대폰 번호 |
| `bio` | `string` | 소개 글, 없으면 빈 글자 (추가 제안) |
| `avatar_url` | `string` \| `null` | 프로필 이미지 주소. 7장 열쇠 포함, 미등록 시 null |

```json
{
  "id": 1,
  "username": "test",
  "name": "MOA User",
  "email": "moa.user@example.com",
  "phone": null,
  "bio": "",
  "avatar_url": null
}
```

- 오류: 0-2. 오류 응답의 공통 오류만 발생

### 2-4. 로그아웃

- 개요: 현재 토큰 폐기
- 요청: `POST /api/auth/logout`, 인증 필요, 본문 없음
- 응답 (200): `{}`
- 오류: 0-2. 오류 응답의 공통 오류만 발생
- 비고: 프론트엔드는 응답을 기다리지 않고 로그아웃 처리 (이미 만료된 토큰의 401 응답도 무시)

### 2-5. 로그인 시간 연장 (추가 제안)

- 개요: 현재 토큰의 만료 시각을 연장 시점부터 3시간 뒤로 재설정
- 요청: `POST /api/auth/extend`, 인증 필요, 본문 없음
- 응답 (200): `{ "expires_at": "2026-10-15T21:05:00+09:00" }` (토큰 문자열은 그대로)
- 오류: 0-2. 오류 응답의 공통 오류만 발생 (이미 만료된 토큰은 401, 재로그인 필요)
- 비고: 연장 안내 시점 등 화면 규칙은 [login_extend.md](login_extend.md)

### 2-6. 아이디 중복확인

- 개요: 회원가입 창의 중복확인 버튼. 가입 요청(2-2) 때도 서버가 다시 확인
- 요청: `GET /api/auth/check-username?username=newbie`, 인증 불필요
- 응답 (200): `{ "username": "newbie", "available": true }` (`available`: 사용 가능 여부, `username`: 앞뒤 공백을 지운 값)
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_USERNAME` | 아이디 비어 있음, 공백 포함 또는 12자 초과 |

### 2-7. 프로필 수정 (추가 제안)

- 개요: 마이페이지 설정의 이름·휴대폰 번호·소개 글 수정. 보낸 항목만 변경
- 요청: `PATCH /api/me`, 인증 필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `name` | `string` | - | 이름, 1~20자 |
| `phone` | `string` | - | 휴대폰 번호. 2-2와 같은 형식, 빈 글자면 삭제 |
| `bio` | `string` | - | 소개 글. 60자 이하, 빈 글자면 삭제 |

- 응답 (200): 2-3. 내 정보 조회와 동일
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_NAME` | 이름 비어 있음 또는 20자 초과 |
| 400 | `INVALID_PHONE` | 휴대폰 번호 형식 오류 |
| 400 | `INVALID_BIO` | 소개 글 60자 초과 |

### 2-8. 프로필 사진 변경 (추가 제안)

- 개요: 프로필 사진 올리기 `POST`, 기본 그림으로 되돌리기 `DELETE`
- 요청: `POST /api/me/avatar`, 인증 필요, `multipart/form-data`의 `file`, jpg/png 10MB 이하 / `DELETE /api/me/avatar`, 인증 필요, 본문 없음
- 응답 (200): 2-3. 내 정보 조회와 동일
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `IMAGE_TOO_LARGE` | 10MB 초과 |
| 400 | `INVALID_IMAGE` | 이미지 아님, jpg·png 외 형식 |

- 비고: 휴대폰 사진 회전 정보 반영 후 중앙 정사각형 256px로 `storage/avatars/avt_xxx.jpg` 저장, EXIF 미저장

### 2-9. 이메일 변경 (추가 제안)

- 요청: `PATCH /api/me/email`, 인증 필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `email` | `string` | O | 새 이메일. 2-2와 같은 형식 검사 |
| `password` | `string` | O | 현재 비밀번호, 본인 확인용 |

- 응답 (200): 2-3. 내 정보 조회와 동일
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `WRONG_PASSWORD` | 비밀번호 불일치 |
| 400 | `INVALID_EMAIL` | 이메일 형식 오류 |
| 400 | `SAME_EMAIL` | 지금 이메일과 같음 |
| 409 | `DUPLICATE_EMAIL` | 다른 회원이 쓰는 이메일 |

### 2-10. 비밀번호 변경 (추가 제안)

- 요청: `PATCH /api/me/password`, 인증 필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `current_password` | `string` | O | 지금 비밀번호 |
| `new_password` | `string` | O | 새 비밀번호. 2-2와 같은 규칙 |

- 응답 (200): `{}`
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `WRONG_PASSWORD` | 지금 비밀번호 불일치 |
| 400 | `INVALID_PASSWORD` | 새 비밀번호 규칙 위반 |
| 400 | `SAME_PASSWORD` | 지금 비밀번호와 같음 |

- 비고: 변경 후 요청 토큰만 유지, 같은 회원의 다른 토큰 폐기로 타 기기 로그아웃

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 3. 이미지 업로드 API

### 3-1. 이미지 업로드

- 개요: 상의·인물 이미지를 서버에 저장하고 이미지 번호 발급
- 요청: `POST /api/images`, 인증 필요, `multipart/form-data`

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `file` | `file` | O | jpg 또는 png, 10MB 이하 |
| `kind` | `string` | O | `garment`(상의) 또는 `person`(인물) |
| `from_sample` | `string` | - | `1`이면 예시 이미지에서 고른 것 (3-2 최근 목록에서 제외), 생략 시 `0` |

- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `image_id` | `string` | 이미지 번호 (`img_` + 12자리) |
| `url` | `string` | 이미지 주소 (7. 이미지 파일 조회 API) |
| `width`, `height` | `integer` | 이미지 크기 (픽셀) |

```json
{
  "image_id": "img_123",
  "url": "/api/files/img_123.jpg?key=...",
  "width": 768,
  "height": 1024
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_KIND` | `kind`가 `garment`·`person`이 아님 |
| 400 | `IMAGE_TOO_LARGE` | 10MB 초과 |
| 400 | `INVALID_IMAGE` | 이미지로 읽을 수 없음, jpg·png 아님 |

- 비고
  - 예시 이미지를 골라도 업로드
  - 이후 추출·합성 요청은 `image_id`로 이미지 지정
  - 휴대폰 사진의 회전 정보(EXIF)를 반영해 바로 세워 저장
  - 긴 변 길이 제한 (미정, 제안 4096px)
  - 업로드 기록을 DB `images` 표에 남기고 작은 이미지(긴 변 240px, `img_..._thumb.jpg`)도 함께 저장 (3-2용)

### 3-2. 최근 사용한 이미지

- 개요: 최근 24시간 동안 직접 업로드한 이미지 목록 (합성하기 1·2단계 더보기 창에서 다시 고르기)
- 요청: `GET /api/images/recent?kind=garment`, 인증 필요 (`kind`: `garment` 또는 `person`)
- 응답 (200): `{ "items": [ ... ] }` 최신순, 최대 12장

| 필드 | 형식 | 설명 |
|---|---|---|
| `image_id` | `string` | 이미지 번호 (다시 고르면 업로드 없이 이 번호로 추출·합성) |
| `url` | `string` | 원본 이미지 주소 |
| `thumb_url` | `string` | 작은 이미지 주소 (목록 표시용) |
| `width`, `height` | `integer` | 원본 크기 (픽셀) |
| `created_at` | `string` | 업로드 시각 (한국 시간) |

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_KIND` | `kind`가 `garment`·`person`이 아님 |

- 비고
  - 제외: 예시 이미지(`from_sample=1`), 다른 회원의 이미지
  - 같은 파일을 여러 번 올리면 가장 최근 것 한 장만
  - 보관: 24시간 지난 기록은 목록 조회 때 DB에서 삭제 (이미지 파일은 유지, 서버 설정 `RECENT_IMAGE_KEEP_HOURS`)

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 4. 상의 영역 추출 API (SAM2)

### 4-1. 상의 영역 추출

- 개요: 사용자가 지정한 좌표(점, 사각형)로 상의 영역을 분할 (SAM2)
- 요청: `POST /api/extract`, 인증 필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `image_id` | `string` | O | 3-1. 이미지 업로드의 상의 이미지 번호 |
| `points` | `array` | 조건 | 좌표 목록 `{ x, y, label }` |
| `points[].x`, `.y` | `number` | O | 위치, 0~1 비율 |
| `points[].label` | `integer` | O | 1 포함, 0 제외 |
| `box` | `object` | 조건 | 상의 감싸는 사각형 (추가 제안) |

- `x`, `y`: 왼쪽 위 0,0 ~ 오른쪽 아래 1,1
- `label`: 화면에서 왼쪽 클릭 1, 오른쪽 클릭 0
- `box`: `{ x1, y1, x2, y2 }`, 0~1 비율

- 조건: 포함 좌표(`label: 1`) 1개 이상 또는 `box` 필수

```json
{
  "image_id": "img_123",
  "points": [
    {
      "x": 0.52,
      "y": 0.41,
      "label": 1
    },
    {
      "x": 0.7,
      "y": 0.2,
      "label": 0
    }
  ]
}
```

- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `extraction_id` | `string` | 추출 번호 (`ext_` + 12자리) |
| `mask_url` | `string` | 상의 영역 흑백 PNG 주소 |
| `cutout_url` | `string` | 상의만 남긴 투명 배경 PNG 주소 |
| `bbox` | `object` | 상의 영역 경계 사각형 `{ x, y, w, h }` |

- `mask_url`: 원본과 같은 크기, 상의 영역 255·나머지 0
- `bbox`: 원본 픽셀 기준

```json
{
  "extraction_id": "ext_456",
  "mask_url": "/api/files/ext_456_mask.png?key=...",
  "cutout_url": "/api/files/ext_456_cutout.png?key=...",
  "bbox": {
    "x": 120,
    "y": 200,
    "w": 400,
    "h": 520
  }
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `NO_POSITIVE_POINT` | 포함 좌표와 `box` 모두 없음 |
| 400 | `INVALID_BOX` | `box`의 왼쪽 위가 오른쪽 아래보다 크거나 같음 |
| 400 | `EMPTY_MASK` | 지정 위치에서 상의 영역을 찾지 못함 |
| 404 | `IMAGE_NOT_FOUND` | 이미지 번호 없음 또는 다른 사용자의 이미지 |

- 비고
  - 호출 시점: 좌표 지정 후 "확인" 시 1회 (좌표 지정 중에는 호출하지 않음)
  - 프론트엔드: 추출 결과 표시 후 "이대로 진행 / 점 다시 찍기" 선택
  - 재지정 시 재호출, 마지막 `extraction_id`를 5-1. 합성 요청에 사용
  - 처리 시간: 수 초 (GPU 사용, 합성 진행 중이면 합성 종료 후 처리)

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 5. 이미지 합성 API (AnyDoor)

- 처리 방식: 합성 요청 → 작업 번호 수신 → 2초 간격 진행 상태 조회 → 결과 조회
- 합성 설정: 50스텝, 1건 약 1분 (스텝 수·시드는 백엔드에서 결정)
- 처리 순서: 요청 순서대로 1건씩 처리 (대기 중이면 `queue_position`으로 순번 표시)

### 5-1. 합성 요청

- 개요: 추출한 상의를 인물 이미지의 착용 영역에 합성하는 작업 등록
- 요청: `POST /api/compose`, 인증 필요, `multipart/form-data`

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `extraction_id` | `string` | O | 4-1. 상의 영역 추출 결과 번호 |
| `person_image_id` | `string` | O | 3-1. 이미지 업로드의 인물 이미지 번호 |
| `area_mask` | `file` | O | 착용 영역 흑백 PNG (지정 영역 255) |
| `garment_mask` | `file` | - | 다듬은 상의 윤곽 흑백 PNG (상의 255) (추가 제안) |
| `refine` | `string` | - | `1`이면 상의 경계 다듬기 (Reference Mask Refine), 생략 시 `0` |
| `shape_control` | `string` | - | `1`이면 칠한 모양 그대로 (Enable Shape Control), 생략 시 `0` |

- `area_mask`: 인물 이미지와 같은 비율, 크기는 서버에서 원본에 맞춤
- `garment_mask`: 상의 이미지와 같은 비율, 크기는 서버에서 원본에 맞춤
  - 생략 시 4-1. 상의 영역 추출의 윤곽(SAM2)으로 합성
  - 용도: 합성하기 3단계 다듬기에서 고친 윤곽 반영 (예: 상의 위 목걸이 제외)
- `refine`, `shape_control`: 합성하기 4단계 뒤 합성 설정 팝업 (AnyDoor 웹 데모의 같은 이름 옵션과 같은 동작)
  - `refine=1`: AnyDoor의 보정 모델(`iseg/coarse_mask_refine.pth`, CPU 약 1~2초)로 상의 윤곽 가장자리를 다듬은 뒤 합성
  - `shape_control=1`: 다시 그릴 영역을 착용 영역을 감싼 사각형 대신 칠한 모양 그대로 (칠하지 않은 곳은 유지, 대신 새 상의가 칠한 모양을 넘지 않음)

- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `job_id` | `string` | 작업 번호 (`job_` + 12자리) |
| `status` | `string` | `queued` (대기) |
| `queue_position` | `integer` | 대기 순번 |

```json
{
  "job_id": "job_789",
  "status": "queued",
  "queue_position": 1
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_AREA_MASK` | 착용 영역 이미지를 읽을 수 없음, 10MB 초과 |
| 400 | `EMPTY_AREA` | 착용 영역이 비어 있음 |
| 400 | `INVALID_GARMENT_MASK` | 상의 윤곽 이미지를 읽을 수 없음, 10MB 초과 (추가 제안) |
| 400 | `EMPTY_GARMENT_MASK` | 상의 윤곽이 비어 있음 (추가 제안) |
| 404 | `EXTRACTION_NOT_FOUND` | 추출 번호 없음 또는 다른 사용자의 추출 결과 |
| 404 | `IMAGE_NOT_FOUND` | 인물 이미지 번호 없음 또는 다른 사용자의 이미지 |

### 5-2. 진행 상태 조회

- 개요: 합성 작업의 진행 상태와 완료 시 결과 번호 조회
- 요청: `GET /api/jobs/{job_id}`, 인증 필요
- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `job_id` | `string` | 작업 번호 |
| `status` | `string` | 작업 상태 (아래 표) |
| `progress` | `number` | 진행률 0~1 |
| `queue_position` | `integer` | 대기 순번 (0: 대기 없음) |
| `result_id` | `string` \| `null` | 결과 번호 (`done`일 때) |
| `error` | `object` \| `null` | 실패 사유 `{ code, message }` (`failed`일 때) |

| `status` | 의미 |
|---|---|
| `queued` | 대기 |
| `running` | 합성 중 |
| `done` | 완료 (`result_id` 사용) |
| `failed` | 실패 (`error` 확인) |

```json
{
  "job_id": "job_789",
  "status": "running",
  "progress": 0.34,
  "queue_position": 0,
  "result_id": null,
  "error": null
}
```

- 실패 사유 (`error.code`)

| `code` | 발생 조건 |
|---|---|
| `COMPOSE_FAILED` | 합성 처리 중 오류 |
| `SERVER_RESTARTED` | 처리 중 서버 재시작으로 작업 중단 (재요청 필요) |

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 404 | `JOB_NOT_FOUND` | 작업 번호 없음 또는 다른 사용자의 작업 |

- 비고: 새로고침 후에도 조회를 이어 가도록 프론트엔드가 `job_id`를 브라우저에 저장

### 5-3. 결과 조회

- 개요: 합성 결과 1건의 이미지 주소와 상태 조회
- 요청: `GET /api/results/{result_id}`, 인증 필요
- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `result_id` | `string` | 결과 번호 (`res_` + 12자리) |
| `image_url` | `string` | 합성 결과 이미지 주소 (PNG) |
| `thumb_url` | `string` | 미리보기 이미지 주소 (JPG) |
| `created_at` | `string` (시각) | 생성 시각 |
| `saved` | `boolean` | 사진첩 저장 여부 |
| `favorite` | `boolean` | 좋아요 여부 |
| `garment_image_id` | `string` | 사용한 상의 이미지 번호 |
| `person_image_id` | `string` | 사용한 인물 이미지 번호 |

- `image_url`: 인물 이미지와 같은 크기 / `thumb_url`: 가로 400px

```json
{
  "result_id": "res_001",
  "image_url": "/api/files/res_001.png?key=...",
  "thumb_url": "/api/files/res_001_thumb.jpg?key=...",
  "created_at": "2026-10-12T20:45:00+09:00",
  "saved": false,
  "favorite": false,
  "garment_image_id": "img_123",
  "person_image_id": "img_124"
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 404 | `RESULT_NOT_FOUND` | 결과 번호 없음 또는 다른 사용자의 결과 |

- 비고
  - 합성 결과는 미저장(`saved: false`)으로 생성되어 내 작업 기록에 표시, 저장 시(`saved: true`) 마이페이지 사진첩에도 표시
  - 저장하지 않은 결과는 생성 24시간 후 자동 삭제 (결과 목록 조회 시 정리)

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 6. 합성 결과 관리 API (작업 기록, 사진첩)

### 6-1. 결과 목록 조회

- 개요: 로그인한 사용자의 합성 결과 목록과 분류별 개수 조회
- 요청: `GET /api/results`, 인증 필요, 조건은 주소 뒤 쿼리 문자열

| 조건 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `saved` | `true` / `false` | - | 저장한 결과 (마이페이지 사진첩) / 미저장 결과, 생략 시 전체 (내 작업 기록) |
| `favorite` | `true` | - | 좋아요 (마이페이지는 `saved=true`와 함께 사용) |
| `date` | `YYYY-MM-DD` | - | 해당 날짜 생성분 (한국 시간 기준) |
| `sort` | `new` / `old` | - | 최신순 (기본) / 오래된순 |
| `limit`, `cursor` | - | - | 분할 조회 (미정) |

- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `items` | `array` | 결과 목록 (항목 필드는 5-3. 결과 조회의 앞 6개와 동일) |
| `counts` | `object` | 분류별 개수: `saved` 저장, `recent` 미저장, `favorite` 저장한 결과 중 좋아요 |
| `next_cursor` | `null` | 분할 조회용 (미정) |

- `counts`: 조회 조건과 무관하게 전체 기준

```json
{
  "items": [
    {
      "result_id": "res_001",
      "thumb_url": "...",
      "image_url": "...",
      "created_at": "...",
      "saved": true,
      "favorite": true
    }
  ],
  "counts": {
    "saved": 20,
    "recent": 6,
    "favorite": 6
  },
  "next_cursor": null
}
```

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_DATE` | `date` 형식 오류 |

### 6-2. 결과 저장 및 좋아요

- 개요: 합성 결과의 사진첩 저장, 좋아요 상태 변경
- 요청: `PATCH /api/results/{result_id}`, 인증 필요, JSON

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `saved` | `boolean` | 조건 | 사진첩 저장 여부 |
| `favorite` | `boolean` | 조건 | 좋아요 여부 |

- 조건: `saved`, `favorite` 중 1개 이상
- 응답 (200): 5-3. 결과 조회와 동일 (변경 후 상태)
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 400 | `INVALID_REQUEST` | `saved`, `favorite` 모두 없음 |
| 404 | `RESULT_NOT_FOUND` | 결과 번호 없음 또는 다른 사용자의 결과 |

### 6-3. 결과 삭제 (미정)

- 요청: `DELETE /api/results/{result_id}`
- 비고: 현재 프론트엔드에 삭제 기능 없음, 도입 여부 미정

### 6-4. 결과 재료 조회 (추가 제안)

- 개요: 결과를 만든 재료 조회. 합성하기 "내 작업 기록"에서 결과를 열 때 1~4단계(상의·인물 사진, 상의 영역, 합성 영역)와 합성 설정을 채움
- 요청: `GET /api/results/{result_id}/source`, 인증 필요
- 응답 (200)

| 필드 | 형식 | 설명 |
|---|---|---|
| `result_id` | `string` | 결과 번호 |
| `garment` | `object` | 상의 사진 `{ image_id, url, width, height }` (3-1 응답과 같은 모양) |
| `person` | `object` | 인물 사진 `{ image_id, url, width, height }` |
| `extraction_id` | `string` | 합성에 쓴 추출 번호 (재합성 때 5-1에 그대로 사용) |
| `garment_mask_url` | `string` | 상의 윤곽 흑백 PNG (다듬은 윤곽, 없으면 4-1 SAM2 윤곽), 7장 열쇠 포함 |
| `area_mask_url` | `string` | 입힐 영역 흑백 PNG, 7장 열쇠 포함 |
| `refine` | `boolean` | 합성 설정: 상의 경계 보정 |
| `shape_control` | `boolean` | 합성 설정: 영역 모양 유지 |

- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 404 | `RESULT_NOT_FOUND` | 결과 번호 없음 또는 다른 사용자의 결과 |
| 404 | `SOURCE_NOT_FOUND` | 재료 파일 중 일부가 없음 (화면은 결과만 표시) |

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 7. 이미지 파일 조회 API

- 개요: 업로드 이미지, 추출 결과, 합성 결과의 실제 파일 조회
- 요청: `GET /api/files/{파일 이름}?key=...`, 위 응답의 `url`, `mask_url`, `cutout_url`, `image_url`, `thumb_url`을 그대로 사용
- 응답 (200): 이미지 파일 (jpg, png)
- 오류

| 상태 코드 | `code` | 발생 조건 |
|---|---|---|
| 404 | `NOT_FOUND` | 파일 없음, 잘못된 파일 이름, 열쇠(`key`) 없음·틀림·만료 |

- 접근 제어: 시간 제한 열쇠 (2026-10-15 결정)
  - 서버가 위 주소를 응답할 때 `?key=만료 시각.서명`을 붙임, 발급 후 3시간 유효
  - 열쇠는 로그인한 본인에게 가는 응답에만 포함 → 본인만 조회 가능
  - 프론트엔드: 주소를 직접 만들거나 오래 보관하지 않기
  - 만료 후: 목록·결과를 다시 조회하면 새 열쇠 발급

[↑ 1. 페이지별 호출 API](#1-페이지별-호출-api)

## 8. 미정 사항

1. 이미지 긴 변 길이 제한: [3-1. 이미지 업로드](#3-1-이미지-업로드)
2. 결과 목록 분할 조회: [6-1. 결과 목록 조회](#6-1-결과-목록-조회)
3. 결과 삭제: [6-3. 결과 삭제](#6-3-결과-삭제-미정)
4. 추가 제안 채택: [2-5. 로그인 시간 연장](#2-5-로그인-시간-연장-추가-제안), [4-1. 상의 영역 추출](#4-1-상의-영역-추출)의 `box`, [5-1. 합성 요청](#5-1-합성-요청)의 `garment_mask`
