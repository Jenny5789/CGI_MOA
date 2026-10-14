# CGI 가상환경 설치 버전

- 처음 설치: 2026-10-11
- 마지막 확인: 2026-10-14 (설치된 패키지가 [pip_freeze.txt](pip_freeze.txt)와 같음)
- 바뀌면 이 파일과 `pip_freeze.txt`를 고치고, 아래 "추가 설치"에 날짜와 함께 적는다 (예전 내용은 git 기록에 남음)

## 기준
- 팀 문서 "3. 실행 환경 및 Package 비교"의 "CGI 환경" 열
- 가상환경 이름: `CGI` (저장소 맨 위 폴더 안, git 제외)
- Python 3.10.0 / CUDA 12.1 / GPU RTX 3080 10GB

## 확인 결과
```
torch 2.5.1+cu121 / cuda available True / numpy 2.2.6 / transformers 5.14.1
```
전체 목록: [pip_freeze.txt](pip_freeze.txt) (아래 추가 설치까지 모두 반영된 최신 목록)

## 설치 순서
```
python -m venv CGI
CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git"
CGI\Scripts\python.exe -m pip install -r requirements.txt
```

추가 설치 (2026-10-12):
```
CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
CGI\Scripts\python.exe -m pip install pycocotools --only-binary :all:
CGI\Scripts\python.exe -m pip install matplotlib --only-binary :all:
CGI\Scripts\python.exe -m pip install lvis==0.5.3 --no-deps
```
- matplotlib 설치 때 contourpy, cycler, fonttools, kiwisolver, pyparsing, python-dateutil, six가 같이 설치됨
- `--no-deps`로 설치해서 torch는 2.5.1+cu121 그대로 유지됨
- GPU에서 `xformers.ops.memory_efficient_attention` 테스트 통과

추가 설치 (2026-10-12, 서버용):
```
CGI\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" python-multipart
```
- 새 패키지 13개만 추가되고 기존 패키지는 바뀌지 않음 (fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.1, starlette 1.7.0 등)
- 설치 후 목록: [pip_freeze.txt](pip_freeze.txt)

## 주요 버전
| 구분 | 패키지 | 버전 |
|---|---|---|
| PyTorch (cu121 인덱스로 별도 설치) | torch / torchvision | 2.5.1+cu121 / 0.20.1+cu121 |
| AnyDoor (requirements.txt 고정) | numpy | 2.2.6 |
| | transformers | 5.14.1 |
| | pytorch-lightning | 1.9.5 |
| | timm | 1.0.28 |
| | open_clip_torch | 3.3.0 |
| | opencv-python (contrib, headless 포함) | 5.0.0.93 |
| | albumentations | 1.3.0 |
| | Pillow | 12.3.0 |
| 객체 추출 (추가) | sam2 (GitHub 설치) | SAM-2 1.0 @ 2b90b9f |
| | segment-anything | 1.0 |
| | kornia | 0.8.2 |
| 추가 설치 (2026-10-12) | xformers (cu124 인덱스, --no-deps) | 0.0.28.post3 |
| | pycocotools | 2.0.11 |
| | lvis (--no-deps) | 0.5.3 |
| | matplotlib | 3.10.9 |

## 제외한 패키지와 이유
- gradio 3.39.0, gradio-client, pydantic, fastapi, starlette: AnyDoor Gradio 데모 전용이고, gradio 3.39.0이 numpy<2를 요구해 numpy 2.2.6과 충돌함

## 체크포인트 (git 제외)
- `checkpoints/sam2/sam2.1_hiera_base_plus.pt`: compositing_lab에서 복사
- `checkpoints/sam/sam_vit_b_01ec64.pth`: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
- BiRefNet (`ZhengPeng7/BiRefNet`): 첫 실행 때 Hugging Face에서 자동 다운로드
