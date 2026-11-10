# MOA 웹 서비스 서버 이미지
# 모델 미적재. 이미지 분할·합성은 MODEL_SERVER_URL의 모델 추론 서버에 HTTP 요청
# 빌드: deploy 폴더에서 docker compose build, 또는 저장소 최상위 폴더에서
#   docker build -f deploy/backend.Dockerfile -t moa-backend:1 .

# Python 3.10: 개발 PC conda 환경 CGI와 같은 버전. slim은 최소 구성 Debian 이미지
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# OpenCV 실행 라이브러리. 박스 선 보정·원본 복원 후처리에 사용
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 패키지 설치를 코드 복사보다 먼저 두어 코드 수정 시 이 층 재사용
COPY deploy/backend-requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# 서버 코드와 후처리 모듈. features는 박스 선 보정·원본 복원만 사용, 모델 코드는 불러오지 않음
COPY backend backend
COPY features features

EXPOSE 8000

# 컨테이너 시작과 동시에 서버 실행. 모든 네트워크 주소에서 요청 수신, 외부 공개는 화면 컨테이너 nginx만
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
