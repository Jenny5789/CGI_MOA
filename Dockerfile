# MOA 백엔드 (FastAPI + SAM2 + AnyDoor) GPU 이미지
# 모델 가중치(약 21GB)는 이미지에 넣지 않고 실행할 때 연결한다 (docker-compose.yml)
# 설치 절차는 README "설치 4·5"와 같은 순서·버전 (Python 3.10, PyTorch 2.5.1 CUDA 12.1)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# python3 = 3.10 (Ubuntu 22.04 기본), git = SAM2·AnyDoor 코드 받기, libgl1·libglib2.0-0 = OpenCV 실행에 필요
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# setuptools<81: pytorch-lightning 1.9.5가 쓰는 pkg_resources 포함 버전
RUN python3 -m pip install --upgrade pip "setuptools<81"
RUN python3 -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
# SAM2 CUDA 확장은 빌드하지 않음 (README: 실패해도 분할 결과에 영향 없음)
RUN SAM2_BUILD_CUDA=0 python3 -m pip install "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"

# requirements.txt를 코드보다 먼저 복사: 코드만 고쳤을 때 위 설치 단계를 다시 하지 않도록
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps

# AnyDoor 공식 코드. 합성 모듈이 run_inference.py의 특정 줄을 바꿔 실행하므로 커밋 고정
# 가중치는 /opt/AnyDoor/path 에 연결 (공식 설정 파일이 가리키는 위치라 설정 수정 불필요)
RUN git clone https://github.com/ali-vilab/AnyDoor /opt/AnyDoor \
    && git -C /opt/AnyDoor checkout 44ca2b2

WORKDIR /app
COPY backend backend
COPY features features

ENV ANYDOOR_DIR=/opt/AnyDoor \
    SAM2_CHECKPOINT=/models/sam2/sam2.1_hiera_base_plus.pt

EXPOSE 8000
# --host 0.0.0.0: 컨테이너 밖(내 브라우저)에서 접속하려면 필요
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]