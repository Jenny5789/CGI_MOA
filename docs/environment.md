# CGI 가상환경 설치 버전

## 기준
- 가상환경: 프로젝트 폴더 안에 `CGI`로 생성
- Python 3.10.0 / CUDA 12.1 / GPU RTX 3080 10GB
- 전체 패키지 목록: [pip_freeze.txt](pip_freeze.txt)

## 설치 확인
- torch 2.5.1+cu121 / cuda available True / numpy 2.2.6 / transformers 5.14.1

## 설치 순서
1. 기본 설치
   ```
   python -m venv CGI
   CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
   CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git"
   CGI\Scripts\python.exe -m pip install -r requirements.txt
   CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
   ```
   - xformers: 합성 속도·메모리 개선, `--no-deps` 설치로 torch 2.5.1+cu121 유지
2. 서버용 설치
   ```
   CGI\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" python-multipart
   ```
   - 기존 패키지(torch, numpy 등) 버전 변경 없음

## 주요 버전
| 구분 | 패키지 | 버전 |
|---|---|---|
| 공통 | torch / torchvision | 2.5.1+cu121 / 0.20.1+cu121 |
| 합성 (AnyDoor) | numpy | 2.2.6 |
| | transformers | 5.14.1 |
| | pytorch-lightning | 1.9.5 |
| | timm | 1.0.28 |
| | open_clip_torch | 3.3.0 |
| | opencv-python (contrib, headless 포함) | 5.0.0.93 |
| | albumentations | 1.3.0 |
| | Pillow | 12.3.0 |
| | xformers | 0.0.28.post3 |
| 추출 (SAM2) | sam2 | SAM-2 1.0 @ 2b90b9f |
| | segment-anything | 1.0 |
| | kornia | 0.8.2 |
| 서버 | fastapi | 0.143.0 |
| | uvicorn | 0.54.0 |
| DB (MySQL) | PyMySQL / SQLAlchemy / cryptography / python-dotenv | 1.2.3 / 2.0.54 / 50.0.2 / 1.2.4 |

## 제외한 패키지
- gradio 3.39.0, gradio-client: AnyDoor Gradio 데모 전용
- 제외 이유: gradio 3.39.0이 numpy<2 요구 → numpy 2.2.6과 충돌

## 모델 파일 (저장소에 없음, AI 기능·서버 담당에게 받기)
- SAM2: `checkpoints/sam2/sam2.1_hiera_base_plus.pt`
- AnyDoor: [../features/composition/README.md](../features/composition/README.md)

## DB (MySQL)
- [database.md](database.md)
