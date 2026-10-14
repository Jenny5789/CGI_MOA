# DB 설정 (MySQL)

- 용도: 서버의 회원, 로그인 증표(토큰) 저장 (명세 2장 로그인·회원가입·내 정보)
- 방식: 팀원마다 **자기 컴퓨터의 MySQL**에 같은 이름의 DB·계정을 만들어 각자 서버 실행
- 접속 정보(비밀번호)는 각자 `backend/.env`에만 저장, GitHub에는 본보기 `backend/.env.example`만 올림
- 상태: 로그인 기능 작업 중 (2026-10-14). 아래 1~4는 지금 해 두면 됨

## 계정 구분

| 계정 | 쓰는 곳 | 비밀번호 보관 |
|---|---|---|
| MySQL `root` | 각자 DB를 만들고 관리할 때 (Workbench) | 본인만 |
| MySQL `moa_app` | 서버 프로그램이 DB에 읽고 쓸 때 (사람이 직접 쓰지 않음) | 각자 `backend/.env` (팀원끼리 공유 안 함) |
| 앱 회원 (`test` 등) | 앱 화면 로그인 | DB의 `users` 표 (비밀번호는 암호화해 저장) |

## 1. MySQL 확인

- MySQL Server 8.0 설치 여부: `C:\Program Files\MySQL\MySQL Server 8.0` 폴더
- 실행 여부: Windows "서비스"에서 `MySQL80` 상태가 "실행 중"
- 화면 도구: MySQL Workbench 8.0
- 없으면 MySQL 공식 설치 프로그램(MySQL Installer)으로 Server 8.0 + Workbench 설치

## 2. DB와 서버 전용 계정 만들기 (Workbench, root로 접속)

- `여기에_비밀번호`를 `moa_app`용으로 새로 정한 비밀번호로 바꿔 실행
- 이미 있으면 그대로 넘어감 (`IF NOT EXISTS`)

```sql
CREATE DATABASE IF NOT EXISTS moa_project CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'moa_app'@'localhost' IDENTIFIED BY '여기에_비밀번호';
GRANT ALL PRIVILEGES ON moa_project.* TO 'moa_app'@'localhost';
```

## 3. 접속 정보 파일 만들기

- `backend/.env.example`을 복사해 `backend/.env`로 이름 변경
- `여기에_비밀번호` 부분만 2번에서 정한 비밀번호로 변경
- 형식: `DATABASE_URL=mysql+pymysql://계정:비밀번호@localhost:3306/DB이름`
- 비밀번호에 `@`, `:`, `/`, `#` 같은 기호가 있으면 접속 주소가 깨질 수 있음 → 영문·숫자 위주 권장
- `backend/.env`는 `.gitignore`에 등록됨 → GitHub에 올라가지 않음

## 4. 파이썬 패키지 (CGI 가상환경)

- `pip install "pymysql[rsa]" sqlalchemy`
- `[rsa]`: MySQL 8 기본 로그인 방식(caching_sha2_password)에 필요한 `cryptography`를 함께 설치
- 확인 버전 (2026-10-14): PyMySQL 1.2.3, SQLAlchemy 2.0.54, cryptography 50.0.2

## 5. 서버가 자동으로 하는 일 (로그인 기능 완성 후)

- 서버를 켜면 `moa_project` 안에 표가 없을 때 자동 생성
- 시험용 회원 `test` / `test1234` 자동 생성 (비밀번호 규칙: 8자 이상, 숫자 포함)

| 표 | 내용 |
|---|---|
| `users` | 회원: 아이디, 이름, 이메일, 비밀번호 해시(원문 저장 안 함), 가입 시각 |
| `sessions` | 로그인 증표: 토큰, 회원 번호, 발급 시각, 만료 시각 |

## 문제 해결

| 증상 | 원인·조치 |
|---|---|
| `Access denied for user 'moa_app'` | `.env` 비밀번호가 2번과 다름 → 비밀번호 확인 |
| `Can't connect to MySQL server` | MySQL이 꺼져 있음 → 서비스 `MySQL80` 시작 |
| `Unknown database 'moa_project'` | 2번 미실행 → SQL 실행 |
| `'cryptography' package is required` | 4번에서 `[rsa]` 빠짐 → `pip install cryptography` |
| `DATABASE_URL이 없습니다` | 3번 미실행 → `backend/.env` 만들기 |
