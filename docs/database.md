# MySQL 데이터베이스 구축

## 1. 개요

- 구성: 팀원마다 자기 PC의 MySQL에 같은 이름으로 구축
- 대상: 정식 설치. MySQL 없이 체험하는 경우 [README 7-2. 설치 6단계 접속 설정 파일 생성](../README.md#7-2-설치)
- 구축 결과

| 항목 | 이름 | 설명 |
|---|---|---|
| 데이터베이스 | `cgi` | 회원 정보, 로그인 세션, 이미지·합성 기록 저장 공간 ([5. 테이블 구성](#5-테이블-구성)) |
| MySQL 계정 | `cgi_app` | 백엔드 서버가 데이터베이스에 접속할 때 쓰는 계정 |

## 2. 구축 순서

### 2-1. MySQL 설치·실행 확인

- 방법 1, 화면: 시작 메뉴에서 "서비스" 실행 → 목록의 `MySQL80` 상태가 "실행 중"이면 정상
- 방법 2, 명령: 시작 메뉴에서 "PowerShell" 실행 후 입력 → `Status`가 `Running`이면 정상

```powershell
Get-Service MySQL*
```

- 서비스 이름: 8.0 설치 기본값 `MySQL80`. 설치 화면의 Windows Service Name에서 바꾼 경우 그 이름
- MySQL 서비스가 없으면 설치 후 다시 확인
  1. https://dev.mysql.com/downloads/installer/ 에서 MySQL Installer 8.0 Windows용 다운로드. 목록에 8.0이 없으면 https://downloads.mysql.com/archives/installer/ 에서 8.0.46 선택
  2. 설치 항목 선택: MySQL Server 8.0, MySQL Workbench
  3. 설치 중 관리자 계정 `root`의 비밀번호 설정, 2-2에서 사용
- 팀 기준 버전: 8.0.46

### 2-2. 데이터베이스·MySQL 계정 생성

1. MySQL Workbench 실행 → MySQL Connections에서 `root` 연결 선택 → `root` 비밀번호 입력
2. 쿼리 창에 아래 SQL 붙여 넣기 → `여기에_비밀번호`를 `cgi_app`에 쓸 새 비밀번호로 변경. 영문·숫자만 사용, `@ : / #` 사용 금지

```sql
CREATE DATABASE IF NOT EXISTS cgi CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'cgi_app'@'localhost' IDENTIFIED BY '여기에_비밀번호';
GRANT ALL PRIVILEGES ON cgi.* TO 'cgi_app'@'localhost';
```

3. 쿼리 창 위 번개 아이콘 Execute 클릭 → 아래 Output에 초록 체크 3개
4. 왼쪽 SCHEMAS 새로고침 → `cgi` 표시 확인

### 2-3. 접속 설정 파일 생성

1. PowerShell에서 Repository 최상위 디렉터리 `CGI_MOA`로 이동. [README 7-2. 설치 3단계 MOA 코드 다운로드, conda 환경 생성](../README.md#7-2-설치)에서 받은 위치

```powershell
cd CGI_MOA
```

2. `backend\.env.example`을 복사해 `backend\.env` 생성

```powershell
Copy-Item backend\.env.example backend\.env
```

3. `backend\.env`를 메모장으로 열기

```powershell
notepad backend\.env
```

4. `여기에_비밀번호`를 2-2에서 정한 비밀번호로 변경 후 저장

```
DATABASE_URL=mysql+pymysql://cgi_app:2-2에서_정한_비밀번호@localhost:3306/cgi
```

- `backend\.env`는 `.gitignore` 등록 파일이라 GitHub에 올라가지 않음

### 2-4. 연결 확인

1. 저장소 최상위 디렉터리에서 백엔드 실행

```powershell
conda activate CGI
python -m uvicorn backend.main:app --port 8000
```

2. 실행 로그 확인

| 로그 | 결과 |
|---|---|
| `DB 연결 완료 (로그인 기능 사용 가능)` | 정상 |
| `DB에 연결하지 못했습니다: ...` | 실패, 뒤의 메시지로 4. 오류별 조치 확인 |
| `DATABASE_URL이 없습니다` | 2-3. 접속 설정 파일 생성 미수행 |

3. 종료: Ctrl+C

## 3. 백엔드 실행 시 자동 처리

| 처리 | 대상 | 시점 |
|---|---|---|
| 테이블 생성 | 회원 `users`, 로그인 세션 `sessions`, 업로드 이미지 `images`, 상의 영역 추출 결과 `extractions`, 합성 작업 `jobs`, 합성 결과 `results` ([5. 테이블 구성](#5-테이블-구성)) | 없으면 생성, 기존 데이터 유지 |
| 열 추가 | 기존 `users`에 전화번호 `phone`, 소개 글 `bio`, 프로필 사진 `avatar`가 없으면 추가 | 실행할 때마다 확인, 기존 데이터 유지 |
| 기록 정리 | 업로드 후 24시간 지난 이미지를 최근 사용한 이미지 목록에서 제외, `images` 기록과 이미지 파일은 유지 | 최근 사용한 이미지 목록 조회 때 |
| 기록 정리 | 저장하지 않은 합성 결과 중 24시간 지난 것의 `results` 기록과 이미지 파일 삭제 | 합성 결과 목록 조회 때 |
| 테스트 계정 생성 | 서비스 로그인용 `test` / `test1234` | 최초 실행 시 1회 |
| 연결 실패 처리 | 백엔드는 실행, 로그인이 필요한 모든 API는 503 `DB_UNAVAILABLE` | 데이터베이스 연결 실패 시 |

## 4. 오류별 조치

- 기준: 백엔드 실행 로그 `DB에 연결하지 못했습니다:` 다음에 표시되는 메시지

| 메시지 | 원인 | 조치 |
|---|---|---|
| `Access denied for user 'cgi_app'@'localhost' (using password: YES)` | `backend/.env` 비밀번호 불일치, 또는 `cgi_app` 계정 없음 | 비밀번호 재확인: 2-3. 접속 설정 파일 생성. 계정이 없으면 2-2. 데이터베이스·MySQL 계정 생성 |
| `Access denied for user 'cgi_app'@'localhost' to database 'cgi'` | 데이터베이스 `cgi` 없음 또는 권한 없음 | 데이터베이스·권한 생성: 2-2. 데이터베이스·MySQL 계정 생성 |
| `Can't connect to MySQL server on 'localhost'` | MySQL 중지 | "서비스" 화면에서 MySQL 서비스 시작, 또는 관리자 권한 PowerShell에서 `Start-Service MySQL80`. 서비스 이름은 2-1 확인 |
| `'cryptography' package is required` | 패키지 누락 | `conda activate CGI` 후 `python -m pip install cryptography` |

## 5. 테이블 구성

- 테이블 6개, 백엔드 실행 시 자동 생성 ([3. 백엔드 실행 시 자동 처리](#3-백엔드-실행-시-자동-처리))

| 테이블 | 저장 내용 | 연결 | 이미지 파일 위치 |
|---|---|---|---|
| `users` | 회원 | - | `storage/avatars` (프로필 사진) |
| `sessions` | 로그인 세션 (토큰 해시) | `users` | - |
| `images` | 업로드 이미지 정보 | `users` | `storage/images` (원본, 작은 이미지) |
| `extractions` | 상의 영역 추출 결과 정보 | `users`, `images` | `storage/extractions` (윤곽, 배경 제거 이미지) |
| `jobs` | 합성 작업 상태, 합성 설정 | `users`, `extractions`, `images` | `storage/jobs` (착용 영역, 다듬은 윤곽) |
| `results` | 합성 결과 정보, 사진첩 저장·좋아요 | `users`, `images`, `jobs`, `extractions` | `storage/results` (결과, 미리보기) |

- 이미지 파일은 DB에 넣지 않고 `storage/`에 저장, 테이블에는 정보와 파일 이름만 저장 (`storage/`는 `.gitignore` 등록, PC마다 따로)
- 시각: DB는 UTC로 저장, API 응답과 결과 목록의 `date` 조건은 한국 시간 (+09:00)
- 합성 대기열·진행 중 작업은 서버 메모리에서 처리, 진행 상태는 `jobs`에도 기록. 서버 재시작 시 처리 중이던 작업은 `failed` (`SERVER_RESTARTED`)
- 테이블 변경: 새 테이블은 자동 생성, 기존 테이블에 새 열 추가는 `backend/db.py`의 `_add_missing_columns`에 등록 (별도 변경 도구 없음)

### 5-1. 외래키

- 외래키 12개 (자식 테이블 기준). 모든 외래키는 부모 테이블의 기본키를 참조

| 테이블 | 컬럼 | 참조 대상 | ON DELETE | 관계 (부모 : 자식) |
|---|---|---|---|---|
| `sessions` | `user_id` | `users.id` | `CASCADE` | 1 : N |
| `images` | `user_id` | `users.id` | `CASCADE` | 1 : N |
| `extractions` | `user_id` | `users.id` | `CASCADE` | 1 : N |
| `extractions` | `image_id` | `images.image_id` | `CASCADE` | 1 : N |
| `jobs` | `user_id` | `users.id` | `CASCADE` | 1 : N |
| `jobs` | `extraction_id` | `extractions.extraction_id` | `CASCADE` | 1 : N |
| `jobs` | `person_image_id` | `images.image_id` | `CASCADE` | 1 : N |
| `results` | `user_id` | `users.id` | `CASCADE` | 1 : N |
| `results` | `job_id` | `jobs.job_id` | `SET NULL` | 1 : N |
| `results` | `extraction_id` | `extractions.extraction_id` | `SET NULL` | 1 : N |
| `results` | `garment_image_id` | `images.image_id` | `NO ACTION` | 1 : N |
| `results` | `person_image_id` | `images.image_id` | `NO ACTION` | 1 : N |

- `ON DELETE`: 부모 레코드를 삭제할 때 자식 레코드의 동작
  - `CASCADE`: 자식 레코드도 삭제 (연쇄 삭제)
  - `SET NULL`: 자식의 외래키 컬럼을 NULL로 변경, 자식 레코드는 유지 (`results`는 재료 보기만 404 `SOURCE_NOT_FOUND`)
  - `NO ACTION`: 자식이 참조 중이면 부모 삭제 거부 (MySQL InnoDB에서 `RESTRICT`와 동일)
- `results.job_id`: 스키마는 1 : N (UNIQUE 제약 없음), 애플리케이션은 작업 하나당 결과를 최대 1개만 생성 (1 : 0..1)
- `jobs.result_id`는 외래키가 아니며 완료된 결과의 ID만 저장
- 회원 삭제: `users` 레코드 하나를 삭제하면 `CASCADE`가 `results`의 `NO ACTION`에 막히므로 `results` → `jobs` → `extractions` → `images` → `users` 순서로 삭제 (회원 삭제 기능은 현재 없음)

## 6. 예전 기록 가져오기

- 대상: 기록을 `storage/`의 json 파일로 저장하던 예전 버전으로 이미지·합성 기록을 만든 PC (새 버전은 같은 정보를 5. 테이블 구성의 테이블에서 읽음)
- 시점: 새 버전으로 백엔드를 한 번 실행해 테이블을 만든 뒤 (3. 백엔드 실행 시 자동 처리)
- 동작
  - 기본은 확인만 하고 DB에 쓰지 않음, `--apply`를 붙여야 반영
  - 여러 번 실행해도 같은 결과 (이미 있는 기록은 건너뜀), json·이미지 파일은 지우지 않음
  - 넣지 못한 기록은 번호와 사유(이미지 파일 없음, 연결된 기록 없음 등)를 출력
- 순서: 앞 단계 기록을 가리키므로 아래 순서 유지

| 순서 | 스크립트 | 옮기는 기록 |
|---|---|---|
| 1 | `scripts\import_image_json.py` | 업로드 이미지 → `images` |
| 2 | `scripts\import_extraction_json.py` | 상의 영역 추출 결과 → `extractions` |
| 3 | `scripts\import_job_json.py` | 합성 작업 → `jobs` |
| 4 | `scripts\import_result_json.py` | 합성 결과 (저장·좋아요 포함) → `results` |

1. 저장소 최상위 디렉터리에서 1번 스크립트를 확인 → 반영 순서로 실행 (출력에서 넣을 개수와 건너뛸 기록 확인)

```powershell
conda activate CGI
python scripts\import_image_json.py
python scripts\import_image_json.py --apply
```

2. 스크립트 이름만 바꿔 2~4번도 같은 방식으로 차례로 실행

- 앞 단계를 반영하기 전에는 뒤 단계의 확인 결과가 "DB에 없음"으로 모두 건너뛰는 것으로 출력됨
