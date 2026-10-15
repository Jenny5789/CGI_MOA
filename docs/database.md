# 데이터베이스(MySQL) 구축

## 1. 개요

- 용도: 회원 정보, 로그인 세션 저장
- 구성: 팀원마다 자기 PC의 MySQL에 같은 이름으로 구축
- 구축 결과

| 항목 | 이름 | 설명 |
|---|---|---|
| 데이터베이스 | `cgi` | 회원 정보, 로그인 세션 저장 공간 |
| MySQL 계정 | `cgi_app` | 백엔드 서버가 데이터베이스에 접속할 때 쓰는 계정 (사람이 로그인하는 계정 아님) |
| 접속 설정 파일 | `backend/.env` | `cgi_app` 비밀번호 저장, GitHub에 올리지 않음 |

## 2. 구축 순서

### 2-1. MySQL 실행 확인

```powershell
Get-Service MySQL80
```

- `Status`가 `Running`이면 정상
- 서비스가 없으면 MySQL Installer로 MySQL Server 8.0, MySQL Workbench 설치

### 2-2. 데이터베이스·MySQL 계정 생성

- MySQL Workbench에서 관리자 계정 `root`로 접속 (`root` 비밀번호: MySQL 설치 시 정한 것)
- 아래 SQL 실행

```sql
CREATE DATABASE IF NOT EXISTS cgi CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'cgi_app'@'localhost' IDENTIFIED BY '여기에_비밀번호';
GRANT ALL PRIVILEGES ON cgi.* TO 'cgi_app'@'localhost';
```

- `여기에_비밀번호`: `cgi_app`에 쓸 새 비밀번호 (영문·숫자, `@ : / #` 사용 금지)

### 2-3. 접속 설정 파일 생성

- 저장소 최상위 디렉터리에서 실행

```powershell
Copy-Item backend\.env.example backend\.env
```

- `backend\.env`의 `여기에_비밀번호`를 2-2에서 정한 비밀번호로 변경

### 2-4. 연결 확인

- 백엔드 실행 시 로그에 `DB 연결 완료 (로그인 기능 사용 가능)` 출력

## 3. 백엔드 실행 시 자동 처리

| 항목 | 내용 |
|---|---|
| 표 생성 | `users` (회원), `sessions` (로그인 세션), 없을 때만 생성 |
| 테스트 계정 | 서비스 로그인용 `test` / `test1234`, 없을 때만 생성 |
| 연결 실패 시 | 백엔드는 실행됨, 로그인이 필요한 모든 API는 503 `DB_UNAVAILABLE` |

## 4. 오류별 조치

| 로그 메시지 | 원인 | 조치 |
|---|---|---|
| `Access denied for user 'cgi_app'` | `backend/.env` 비밀번호 불일치 | 2-3. 접속 설정 파일 생성의 비밀번호 확인 |
| `Can't connect to MySQL server` | MySQL 중지 | `Start-Service MySQL80` (관리자 PowerShell) |
| `Unknown database 'cgi'` | 데이터베이스 미생성 | 2-2. 데이터베이스·MySQL 계정 생성 수행 |
| `'cryptography' package is required` | 패키지 누락 | `CGI\Scripts\python.exe -m pip install cryptography` |
| `DATABASE_URL이 없습니다` | `backend/.env` 없음 | 2-3. 접속 설정 파일 생성 수행 |
