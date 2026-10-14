# DB 설정 (MySQL)

- 용도: 회원, 로그인 토큰 저장
- 팀원마다 자기 컴퓨터 MySQL에 같은 이름의 DB·계정 생성
- 비밀번호는 각자 `backend/.env`에만 (GitHub에는 `backend/.env.example`만)

## 계정

| 계정 | 용도 | 비밀번호 보관 |
|---|---|---|
| MySQL `root` | DB 관리 (Workbench) | 본인만 |
| MySQL `cgi_app` | 서버 프로그램 전용 | `backend/.env` (공유 안 함) |
| 앱 회원 `test` 등 | 앱 로그인 | `users` 표 (해시 저장) |

## 1. MySQL 확인

- 설치: `C:\Program Files\MySQL\MySQL Server 8.0`
- 실행: Windows "서비스" → `MySQL80` "실행 중"
- 없으면 MySQL Installer로 Server 8.0 + Workbench 설치

## 2. DB·계정 만들기 (Workbench, root 접속)

- `여기에_비밀번호`를 `cgi_app`용 새 비밀번호로 바꿔 실행 (영문·숫자, `@ : / #` 금지)

```sql
CREATE DATABASE IF NOT EXISTS cgi CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'cgi_app'@'localhost' IDENTIFIED BY '여기에_비밀번호';
GRANT ALL PRIVILEGES ON cgi.* TO 'cgi_app'@'localhost';
```

## 3. `backend/.env` 만들기

- `backend/.env.example` 복사 → `backend/.env`
- `여기에_비밀번호`만 2번 비밀번호로 변경

## 4. 패키지 (CGI 가상환경)

- `pip install "pymysql[rsa]" sqlalchemy python-dotenv`
- 확인 버전 (2026-10-14): PyMySQL 1.2.3, SQLAlchemy 2.0.54, cryptography 50.0.2

## 5. 서버 실행 시 자동

- 로그 `DB 연결 완료 (로그인 기능 사용 가능)` → 정상
- 표 `users`, `sessions` 자동 생성
- 시험 회원 `test` / `test1234` 자동 생성
- 연결 실패해도 서버는 켜짐, 로그인 주소만 503

## 문제 해결

| 증상 | 조치 |
|---|---|
| `Access denied for user 'cgi_app'` | `.env` 비밀번호 확인 |
| `Can't connect to MySQL server` | 서비스 `MySQL80` 시작 |
| `Unknown database 'cgi'` | 2번 SQL 실행 |
| `'cryptography' package is required` | `pip install cryptography` |
| `DATABASE_URL이 없습니다` | 3번 `backend/.env` 만들기 |
