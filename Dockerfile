# MOA 백엔드 이미지

FROM nvidia/cuda:12.1.1-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu121

RUN python3 -m pip install --upgrade pip "setuptools<81"

RUN SAM2_BUILD_CUDA=0 python3 -m pip install \
    "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

RUN python3 -m pip install xformers==0.0.28.post3 --no-deps \
    --index-url https://download.pytorch.org/whl/cu121

RUN git clone https://github.com/ali-vilab/AnyDoor /opt/AnyDoor \
    && git -C /opt/AnyDoor checkout 44ca2b2

COPY backend backend
COPY features features

ENV ANYDOOR_DIR=/opt/AnyDoor \
    SAM2_CHECKPOINT=/models/sam2/sam2.1_hiera_base_plus.pt

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]