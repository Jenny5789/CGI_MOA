# 데이터베이스(MySQL) 구축

## 1. 개요

- 용도: 회원 정보, 로그인 세션 저장
- 구성: 팀원마다 자기 PC의 MySQL에 같은 이름의 DB·계정 생성
- 접속 비밀번호: 각자 `backend/.env`에만 저장 (GitHub에는 예시 파일 `backend/.env.example`만)

## 2. MySQL 계정

| 계정 | 용도 | 만드는 방법 | 비밀번호 보관 |
|---|---|---|---|
| `root` | DB·계정 생성 시 접속 (MySQL Workbench) | MySQL 설치 시 자동 생성 | 본인 |
| `cgi_app` | 백엔드 서버의 DB 접속 | 3-2. DB·계정 생성의 SQL로 직접 생성 | `backend/.env` (공유 금지) |

## 3. 구축 순서

### 3-1. MySQL 실행 확인

```powershell
Get-Service MySQL80
```

- `Status`가 `Running`이면 정상
- 서비스가 없으면 MySQL Installer로 MySQL Server 8.0, MySQL Workbench 설치

### 3-2. DB·계정 생성

- MySQL Workbench에서 `root`로 접속 후 실행

```sql
CREATE DATABASE IF NOT EXISTS cgi CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'cgi_app'@'localhost' IDENTIFIED BY '여기에_비밀번호';
GRANT ALL PRIVILEGES ON cgi.* TO 'cgi_app'@'localhost';
```

- `여기에_비밀번호`: `cgi_app`용 새 비밀번호 (영문·숫자, `@ : / #` 사용 금지)

### 3-3. 접속 설정 파일 생성

- 저장소 최상위 디렉터리에서 실행

```powershell
Copy-Item backend\.env.example backend\.env
```

- `backend\.env`의 `여기에_비밀번호`를 3-2에서 정한 비밀번호로 변경

### 3-4. 연결 확인

- 백엔드 실행 시 로그에 `DB 연결 완료 (로그인 기능 사용 가능)` 출력

## 4. 백엔드 실행 시 자동 처리

| 항목 | 내용 |
|---|---|
| 표 생성 | `users` (회원), `sessions` (로그인 세션), 없을 때만 생성 |
| 테스트 계정 | `test` / `test1234`, 없을 때만 생성 |
| 연결 실패 시 | 백엔드는 실행됨, 로그인이 필요한 모든 API는 503 `DB_UNAVAILABLE` |

## 5. 오류별 조치

| 로그 메시지 | 원인 | 조치 |
|---|---|---|
| `Access denied for user 'cgi_app'` | `backend/.env` 비밀번호 불일치 | 3-3. 접속 설정 파일 생성의 비밀번호 확인 |
| `Can't connect to MySQL server` | MySQL 중지 | `Start-Service MySQL80` (관리자 PowerShell) |
| `Unknown database 'cgi'` | DB 미생성 | 3-2. DB·계정 생성 수행 |
| `'cryptography' package is required` | 패키지 누락 | `CGI\Scripts\python.exe -m pip install cryptography` |
| `DATABASE_URL이 없습니다` | `backend/.env` 없음 | 3-3. 접속 설정 파일 생성 수행 |
