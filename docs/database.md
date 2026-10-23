# MySQL 데이터베이스 구축

## 1. 개요

- 구성: 팀원마다 자기 PC의 MySQL에 같은 이름으로 구축
- 구축 결과

| 항목 | 이름 | 설명 |
|---|---|---|
| 데이터베이스 | `cgi` | 회원 정보, 로그인 세션 저장 공간 |
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

1. PowerShell에서 저장소 최상위 디렉터리 `CGI_MOA`로 이동. [environment.md 4-2. 저장소 받기](environment.md#4-2-저장소-받기)에서 받은 위치

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
$env:ANYDOOR_DIR = "$PWD\checkpoints\AnyDoor"
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
| 테이블 생성 | 회원 `users`, 로그인 세션 `sessions`, 업로드 기록 `images` | 없으면 생성, 기존 데이터 유지 |
| 열 추가 | 기존 `users`에 전화번호 `phone`, 소개 글 `bio`, 프로필 사진 `avatar`가 없으면 추가 | 실행할 때마다 확인, 기존 데이터 유지 |
| 기록 정리 | `images`에서 24시간 지난 업로드 기록 삭제, 이미지 파일은 유지 | 최근 사용한 이미지 목록 조회 때 |
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
