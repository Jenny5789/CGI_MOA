# MOA 모델 추론 서버 이미지
# 빌드: 저장소 최상위 폴더에서
#   docker build -f model_server/Dockerfile -t moa-model .
# 가중치는 이미지에 넣지 않고 실행 시 읽기 전용 폴더로 연결, model_server/README.md 참고

# CUDA 12.1 실행 라이브러리만 포함한 Ubuntu 22.04. Python 3.10 기본 포함 버전
FROM nvidia/cuda:12.1.1-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# python3, pip, GitHub 코드 내려받기용 git, OpenCV 실행 라이브러리
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip git libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# PyTorch와 xformers: CUDA 12.1용 저장소에서 서로 맞는 버전을 한 번에 설치
RUN python3 -m pip install torch==2.5.1 torchvision==0.20.1 xformers==0.0.28.post3 \
    --index-url https://download.pytorch.org/whl/cu121

# 나머지 패키지: 자주 바뀌지 않는 층이라 코드보다 먼저 설치해 재빌드 시간 단축
COPY model_server/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt

# SAM2: 개발 PC와 같은 커밋. CUDA 확장 빌드 생략, 기능 동일
RUN SAM2_BUILD_CUDA=0 python3 -m pip install --no-deps \
    "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"

# AnyDoor 공식 코드: 개발 PC와 같은 커밋 44ca2b2. 가중치 경로 설정은 ANYDOOR_CKPT로 대체
RUN git clone https://github.com/ali-vilab/AnyDoor /opt/AnyDoor \
    && git -C /opt/AnyDoor checkout 44ca2b2 \
    && rm -rf /opt/AnyDoor/.git

# MOA 코드: 모델 모듈과 서버 코드만 복사
WORKDIR /app
COPY features features
COPY model_server model_server

# 가중치 위치: 실행 시 /weights 아래로 연결
ENV ANYDOOR_DIR=/opt/AnyDoor \
    ANYDOOR_CKPT=/weights/anydoor/official_fp16.ckpt \
    SAM2_CHECKPOINT=/weights/sam2/sam2.1_hiera_base_plus.pt

EXPOSE 8100

# 컨테이너 시작과 동시에 모델 서버 실행, 적재·예열은 서버 안에서 자동 진행
CMD ["python3", "-m", "uvicorn", "model_server.app:app", "--host", "0.0.0.0", "--port", "8100"]
