# 설치 및 실행

- 대상: Python 가상환경(conda)에 직접 설치해 개발 서버를 실행하는 절차
- Docker로 한 번에 실행: [local/README.md](../local/README.md)
- 요구 사양: [README 7. 설치 및 실행](../README.md#7-설치-및-실행)
- 설치 오류 조치: [개발 환경 참고](environment.md#2-설치-오류별-조치)

## 1. 용어

| 용어 | 뜻 |
|---|---|
| 명령 입력 창 | 명령어를 입력해 프로그램을 실행하는 창. 이 문서에서는 Windows PowerShell, Anaconda Prompt 사용 |
| Anaconda Prompt | Anaconda 설치 시 함께 설치되는 명령 입력 창. 시작 메뉴에서 `Anaconda Prompt` 검색 후 실행, `conda` 명령 사용 가능 |
| conda 환경 | MOA 전용 Python과 패키지를 PC의 다른 Python과 분리해 설치하는 공간. MOA는 이름 `CGI` 사용 |
| 패키지 | Python 프로그램이 불러 쓰는 라이브러리. `pip` 명령으로 설치 |
| 가중치 파일 | 학습을 마친 AI 모델의 매개변수를 담은 파일. SAM2·AnyDoor 실행에 필요 |
| 저장소 (Repository) | GitHub에 올린 MOA 코드 전체 |

## 2. 설치

| 단계 | 내용 | 명령 입력 창 |
|---|---|---|
| 1단계 | NVIDIA 그래픽 드라이버 설치 | Windows PowerShell (확인용) |
| 2단계 | Git · Anaconda · Node.js 설치 | Windows PowerShell |
| 3단계 | MOA 코드 다운로드, conda 환경 생성 | Anaconda Prompt |
| 4단계 | Python 패키지 설치 | Anaconda Prompt |
| 5단계 | AI 모델 코드 · 가중치 파일 다운로드 | Anaconda Prompt |
| 6단계 | 접속 설정 파일 생성 | Anaconda Prompt |
| 7단계 | 설치 확인 | Anaconda Prompt |

- 단계 이름 클릭 시 명령어와 설명 표시

<details>
<summary><b>1단계 · NVIDIA 그래픽 드라이버 설치</b></summary>

<br>

- 목적: PyTorch의 GPU 사용
- 설치: https://www.nvidia.com/ko-kr/drivers/ 에서 그래픽 카드 모델에 맞는 드라이버 설치 후 PC 재시작
- 확인: Windows PowerShell에서 `nvidia-smi` 입력, 결과 오른쪽 위 `CUDA Version` 12.1 이상
- CUDA(GPU 연산 도구)는 4단계 PyTorch에 포함, 별도 설치 불필요

</details>

<details>
<summary><b>2단계 · Git · Anaconda · Node.js 설치</b></summary>

<br>

- 명령 입력 창: Windows PowerShell

```powershell
winget install -e --id Git.Git
winget install -e --id Anaconda.Anaconda3
winget install -e --id OpenJS.NodeJS.LTS --version 24.22.1
```

| 프로그램 | 용도 |
|---|---|
| Git | 코드 다운로드 프로그램. MOA·AnyDoor 코드 다운로드, SAM2 패키지 설치에 사용 |
| Anaconda | Python과 conda 환경 관리 프로그램. Anaconda·Miniconda 설치 PC는 두 번째 줄 생략 |
| Node.js 24 | JavaScript 실행 프로그램. 프론트엔드 개발 서버 실행, `npm` 명령 포함 |

- 설치 중 약관 동의 질문 시 `Y` 입력
- 설치 후 열린 PowerShell 창 모두 닫기 (새 창부터 설치한 프로그램 인식)

</details>

<details>
<summary><b>3단계 · MOA 코드 다운로드 · conda 환경 생성</b></summary>

<br>

- 명령 입력 창: Anaconda Prompt

```bat
cd C:\
git clone https://github.com/Jenny5789/CGI_MOA.git
cd CGI_MOA
conda create -n CGI python=3.10 -c conda-forge --override-channels -y
conda activate CGI
```

| 명령 | 내용 |
|---|---|
| `cd C:\` | C 드라이브 최상위 폴더로 이동 |
| `git clone ...` | MOA Repository를 `C:\CGI_MOA` 폴더에 다운로드 |
| `cd CGI_MOA` | 다운로드한 폴더로 이동 |
| `conda create ...` | Python 3.10이 설치된 conda 환경 `CGI` 생성 |
| `conda activate CGI` | conda 환경 `CGI` 사용 시작. 명령 줄 앞 `(base)`가 `(CGI)`로 바뀌면 정상 |

- 다른 폴더 사용 시 경로에 한글·공백이 없는 폴더 권장
- Anaconda Prompt를 새로 열 때마다 `cd C:\CGI_MOA`, `conda activate CGI` 입력 필요

</details>

<details>
<summary><b>4단계 · Python 패키지 설치</b></summary>

<br>

- 목적: SAM2·AnyDoor·백엔드 서버 실행에 필요한 패키지를 conda 환경 `CGI`에 설치
- 명령 입력 창: Anaconda Prompt, 명령 줄 앞 `(CGI)` 표시 상태

```bat
python -m pip install --upgrade pip
python -m pip install "setuptools<81"
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"
python -m pip install -r requirements.txt
python -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
python -c "import torch; print(torch.cuda.is_available())"
```

| 줄 | 설치 대상 | 용도 |
|---|---|---|
| 1 | pip | 패키지 설치 도구 최신화 |
| 2 | setuptools 81 미만 | AnyDoor가 사용하는 pytorch-lightning 1.9.5의 필요 모듈 `pkg_resources` 포함 버전. 81 이상 설치 시 서버 예열 중 `ModuleNotFoundError` |
| 3 | PyTorch 2.5.1, torchvision 0.20.1 | SAM2·AnyDoor를 GPU에서 실행하는 딥러닝 프레임워크, CUDA 12.1용 |
| 4 | SAM2 | 점 지정 기반 영역 추출 모델 코드. 커밋 고정으로 PyTorch 버전 변경 방지 |
| 5 | `requirements.txt` 목록 | AnyDoor 실행(pytorch-lightning, transformers, OpenCV 등), 백엔드 서버(FastAPI, Uvicorn), DB 접속(SQLAlchemy, PyMySQL) |
| 6 | xformers 0.0.28.post3 | 어텐션 연산 최적화로 합성 속도 향상·GPU 메모리 절감. `--no-deps`로 PyTorch 버전 변경 방지 |
| 7 | - | PyTorch의 GPU 인식 확인. 결과 `True` 시 정상 |

- `Failed to build the SAM 2 CUDA extension` 안내: SAM2 일부 후처리 가속 기능만 제외, 추출 결과 영향 없음

</details>

<details>
<summary><b>5단계 · AI 모델 코드 · 가중치 파일 다운로드</b></summary>

<br>

- 목적: 합성 모델 AnyDoor의 코드와 SAM2·AnyDoor 가중치 파일 준비
- 명령 입력 창: Anaconda Prompt, 명령 줄 앞 `(CGI)` 표시 상태

```bat
git clone https://github.com/ali-vilab/AnyDoor checkpoints\AnyDoor
git -C checkpoints\AnyDoor checkout 44ca2b2
mkdir checkpoints\sam2
mkdir checkpoints\AnyDoor\path
curl.exe -L -o checkpoints\sam2\sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
curl.exe -L -o "checkpoints\AnyDoor\path\epoch=1-step=8687.ckpt" "https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch=1-step=8687.ckpt"
curl.exe -L -o checkpoints\AnyDoor\path\dinov2_vitg14_pretrain.pth https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth
conda env config vars set ANYDOOR_DIR=C:\CGI_MOA\checkpoints\AnyDoor -n CGI
conda deactivate
conda activate CGI
```

| 줄 | 내용 |
|---|---|
| 1~2 | AnyDoor 코드를 `checkpoints\AnyDoor`에 다운로드, 검증한 커밋 `44ca2b2`로 고정. `detached HEAD` 안내는 정상 |
| 3~4 | 가중치 파일 저장 폴더 생성 |
| 5~7 | 가중치 파일 3개 다운로드 |
| 8~10 | AnyDoor 폴더 위치를 환경 변수 `ANYDOOR_DIR`로 conda 환경 `CGI`에 등록 후 다시 활성화 |

| 가중치 파일 | 모델 | 용도 | 크기 |
|---|---|---|---|
| `sam2.1_hiera_base_plus.pt` | SAM 2.1 Base+ | 상의·착용 영역 추출 | 약 309MB |
| `epoch=1-step=8687.ckpt` | AnyDoor | 착용 합성 | 약 16.8GB |
| `dinov2_vitg14_pretrain.pth` | DINOv2 ViT-g/14 | AnyDoor가 상의의 모양·질감 정보를 읽는 데 사용 | 약 4.5GB |

- 커밋 고정 이유: MOA 합성 모듈이 실행 시 AnyDoor `run_inference.py`의 특정 코드 줄 교체, 다른 버전에서는 해당 줄 불일치
- `path` 폴더: AnyDoor 공식 설정 파일이 가리키는 가중치 파일 위치, 설정 파일 수정 불필요
- `ANYDOOR_DIR` 미등록 시 기본값 `Desktop\AnyDoor` 탐색. Repository를 다른 폴더에 받은 경우 8번째 줄 경로 변경
- 다운로드 중단 시 해당 `curl.exe` 줄만 다시 입력. 파일 크기 확인·다른 다운로드 경로: [모델 파일 확인](environment.md#3-모델-파일-확인)

</details>

<details>
<summary><b>6단계 · 접속 설정 파일 생성</b></summary>

<br>

- 목적: 백엔드 서버의 DB 위치, 프론트엔드의 백엔드 서버 주소 지정
- 명령 입력 창: Anaconda Prompt

```bat
mkdir storage
copy backend\.env.sqlite.example backend\.env
copy frontend\.env.mixed.example frontend\.env.local
```

| 생성 대상 | 내용 |
|---|---|
| `storage\` | 업로드 사진·합성 결과·SQLite DB 파일 저장 폴더 |
| `backend\.env` | DB 위치 `DATABASE_URL`. SQLite 파일 `storage\moa_trial.db` 사용 |
| `frontend\.env.local` | API 요청 모드 `mixed` (실제 서버에 있는 기능은 실제 서버로, 나머지는 화면용 가짜 응답. `mock`은 전부 가짜, `real`은 전부 실제 서버), 백엔드 서버 주소 `http://localhost:8000` |

- 백엔드 서버 첫 실행 시 DB 파일, 테스트 계정 `test` / `test1234` 자동 생성
- `.env`, `.env.local`, `storage\`: 개인 설정·사용자 데이터로 Git 업로드 제외
- 팀 공용 MySQL 사용 시 이 단계 대신 [MySQL 데이터베이스 구축](database.md) 진행

</details>

<details>
<summary><b>7단계 · 설치 확인</b></summary>

<br>

- 목적: 패키지 버전, GPU, AnyDoor 폴더, SAM2 가중치 파일, `backend\.env` 점검 (18개 항목)
- 명령 입력 창: Anaconda Prompt, 명령 줄 앞 `(CGI)` 표시 상태

```bat
python scripts\check_env.py
```

- 정상: 모든 항목 `[OK]`. 단 `가상환경 CGI` 항목은 conda 환경에서 `[NG]`가 정상 (아래 표)

| `[NG]` 항목 | 원인 · 조치 |
|---|---|
| 가상환경 CGI | 점검 스크립트의 venv 방식 환경만 인식, conda 환경에서는 항상 `[NG]`. 표시된 실행 경로 끝이 `envs\CGI\python.exe`이면 정상 |
| AnyDoor 폴더 (경로 `Desktop\AnyDoor`) | `ANYDOOR_DIR` 미등록. 5단계 8~10번째 줄 다시 입력 |

- AnyDoor·DINOv2 가중치 파일은 점검 대상 제외. 크기 확인: [모델 파일 확인](environment.md#3-모델-파일-확인)
- `A matching Triton is not available` 경고: Windows 환경 공통 안내, 무시

</details>

## 3. 백엔드 서버 실행

- 명령 입력 창: Anaconda Prompt

```bat
cd C:\CGI_MOA
conda activate CGI
python -m uvicorn backend.main:app --port 8000
```

- 가중치 파일 로드·예열 약 2분
- 상태 확인: 웹 브라우저에서 http://localhost:8000/api/health 접속
  - `"status": "ok"`: 백엔드 서버 실행 중
  - `"warmup": "done"`: 합성 준비 완료
- API 테스트 페이지: http://localhost:8000/docs
  - 자물쇠 표시 API: `POST /api/auth/login` 응답의 `token` 값을 `Authorize` 버튼에 입력 후 실행
- 환경 변수 목록: [backend/README.md](../backend/README.md#3-환경-변수)

## 4. 프론트엔드 개발 서버 실행

- 명령 입력 창: 새 Anaconda Prompt (백엔드 서버 창 유지)

```bat
cd C:\CGI_MOA\frontend
npm install
npm run dev -- --port 5180 --strictPort
```

| 명령 | 내용 |
|---|---|
| `npm install` | 프론트엔드 패키지 설치, 최초 1회 |
| `npm run dev ...` | 5180번 포트로 개발 서버 실행. 5180번 사용 중이면 다른 포트로 바꾸지 않고 종료 (터널 주소 불일치 방지) |

- 접속: 웹 브라우저에서 http://localhost:5180 , 테스트 계정 `test` / `test1234`

| 구성 | 포트 |
|---|---|
| 백엔드 서버 (FastAPI) | 8000 |
| 프론트엔드 개발 서버 (Vite) | 5180 |

## 5. 외부 접속 · Cloudflare 터널

- 용도: 휴대폰·외부 PC에서 시연
- 조건: 백엔드 서버·프론트엔드 개발 서버 실행 중
- 명령 입력 창: 새 Anaconda Prompt

```bat
winget install --id Cloudflare.cloudflared
cloudflared tunnel --no-autoupdate --url http://localhost:5180
```

- 첫 줄: cloudflared 설치, 최초 1회. 설치 후 Anaconda Prompt를 새로 열어 두 번째 줄 입력
- 두 번째 줄 실행 로그의 `https://….trycloudflare.com` 주소로 접속
- 프론트엔드 개발 서버가 `/api` 요청을 백엔드 서버(8000번)로 전달하므로 터널 1개로 전체 기능 사용
- 별도 설정 불필요 (`frontend/vite.config.js`의 `allowedHosts`에 `.trycloudflare.com` 이미 등록)
- 터널 창 종료 시 주소 만료, 실행마다 새 주소 발급
