# 서비스 배포 구성

MySQL·웹 서비스 서버·화면을 Docker Compose 하나로 실행하는 구성. 이미지 분할·합성은 GPU가 있는 컴퓨터의 모델 추론 서버 `model_server/`가 담당하고, 웹 서비스 서버가 HTTP로 호출.

## 1. 구성

```
사용자 브라우저 ──▶ moa-frontend :WEB_PORT ──/api──▶ moa-backend :8000 ──▶ moa-mysql :3306
                                                        └──HTTP──▶ 모델 추론 서버 :8100, GPU 컴퓨터
```

| 컨테이너 | 이미지 | 역할 | 외부 공개 |
|---|---|---|---|
| `moa-frontend` | `deploy/frontend.Dockerfile`, nginx | 화면 파일 제공, `/api` 요청을 웹 서비스 서버로 전달 | `WEB_PORT`, 기본 8080 |
| `moa-backend` | `deploy/backend.Dockerfile`, Python 3.10 | 로그인, 사진·결과 관리, 합성 대기열, 박스 선 보정·원본 복원 후처리. 모델 미적재 | 없음 |
| `moa-mysql` | `mysql:8.0` | 회원·세션·사진·작업·결과 기록 | 없음 |

| 데이터 보관 볼륨 | 내용 |
|---|---|
| `mysql-data` | MySQL 데이터 |
| `storage` | 올린 사진, 분할 마스크, 합성 결과, 파일 주소 서명 키 |

## 2. 파일

| 파일 | 역할 |
|---|---|
| `docker-compose.yml` | 세 컨테이너, 볼륨, 상태 확인, 자동 재시작 |
| `backend.Dockerfile`, `backend.Dockerfile.dockerignore`, `backend-requirements.txt` | 웹 서비스 서버 이미지. PyTorch 미포함 |
| `frontend.Dockerfile`, `frontend.Dockerfile.dockerignore`, `nginx.conf` | 화면 이미지. Node.js 빌드 후 nginx에 결과만 복사 |
| `.env.example` | 설정값 본보기. `.env`로 복사해 사용, `.env`는 Git 제외 |

## 3. 실행

`deploy` 폴더에서 실행.

```
copy .env.example .env
docker compose up -d --build
docker compose ps
```

- `.env`의 `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`: 영문·숫자만
- `.env`의 `MODEL_SERVER_URL`
  - 학교 VM: 모델 추론 서버가 실행 중인 개발 PC 주소, 예 `http://192.168.24.106:8100`
  - 개발 PC에서 시험: `http://host.docker.internal:8100`
- 모델 추론 서버에 `MODEL_TOKEN`을 설정했다면 같은 값 입력
- 확인
  - `http://localhost:8080/api/health`의 `"warmup":"done"`: 모델 추론 서버 준비 완료 확인
  - `docker logs moa-backend`의 `DB 연결 완료`, `AnyDoor 예열 끝`
  - 화면 `http://localhost:8080`, 첫 실행 시 시험 계정 `test` / `test1234` 자동 생성

## 4. 멈추기와 데이터

| 명령 | 결과 |
|---|---|
| `docker compose stop` | 멈춤, `docker compose start`로 다시 실행 |
| `docker compose down` | 컨테이너 삭제, 볼륨 데이터 유지 |
| `docker compose down -v` | 컨테이너와 볼륨 데이터 모두 삭제. 회원·사진·결과 전부 삭제 |

- 코드 수정 후 `docker compose up -d --build`: 바뀐 이미지만 다시 빌드·실행

## 5. 이미지 크기

| 이미지 | 크기 | 비고 |
|---|---:|---|
| `moa-backend:1` | 620MB | Python 3.10 slim + FastAPI·DB·OpenCV |
| `moa-frontend:1` | 1.29GB | nginx + 화면 빌드 결과. 예시 이미지 `frontend/public/assets` 602MB 포함 |
| `mysql:8.0` | 공식 이미지 | |
