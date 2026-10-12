# MOA 백엔드 (FastAPI)

웹 화면(`frontend/`)이 요청을 보내는 서버입니다. 로그인, 상의 추출(SAM), 합성, 작업 기록을 처리하고 기록은 MySQL에 저장합니다.

## 폴더 배치

서버 코드는 바로 옆 폴더의 SAM과 AnyDoor 코드를 찾습니다. 이 두 폴더와 모델 파일은 용량이 커서 저장소에 없으니 각자 받아서 아래처럼 둡니다.

```
CGI_MOA/
  backend/               이 폴더
  frontend/
  segment-anything/      https://github.com/facebookresearch/segment-anything  (아래 "SAM과 SAM2" 참고)
    checkpoints/sam_vit_h_4b8939.pth     (약 2.5GB, 위 저장소 안내의 vit_h 모델)
  AnyDoor/               https://github.com/ali-vilab/AnyDoor  (합성을 AnyDoor로 바꿀 때 필요)
    checkpoints/epoch=1-step=8687.ckpt   (16.8GB)
    checkpoints/dinov2_vitg14_pretrain.pth (4.5GB)
```

## 준비

### 1. 파이썬 환경
서지섭 PC에서 확인한 버전: Python 3.10.11, torch 2.0.0+cu118, FastAPI 0.141.1.

```
python -m venv venv
venv\Scripts\activate
pip install torch==2.0.0 torchvision==0.15.1 --index-url https://download.pytorch.org/whl/cu118
pip install -r backend/requirements.txt
```

SAM과 AnyDoor에 필요한 나머지 라이브러리는 각 저장소의 안내를 따릅니다.

### 2. MySQL
MySQL을 설치하고 DB와 접속 계정을 하나씩 만듭니다. 표(회원, 추출 기록, 합성 작업)는 서버가 처음 켜질 때 자동으로 만듭니다.

```sql
CREATE DATABASE moa_project CHARACTER SET utf8mb4;
CREATE USER 'moa_app'@'localhost' IDENTIFIED BY '자기가_정한_비밀번호';
GRANT ALL PRIVILEGES ON moa_project.* TO 'moa_app'@'localhost';
```

### 3. 접속 정보
`.env.example`을 복사해 `.env`를 만들고 위에서 정한 비밀번호를 적습니다. `.env`는 Git에 올리지 않습니다.

## 실행

MySQL을 켠 뒤 `backend` 폴더에서:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```

http://localhost:8000/health 가 `{"status":"ok"}`면 정상입니다. 처음 켜질 때 시험용 계정 `test / test1234`가 자동으로 만들어집니다.

SAM과 AnyDoor는 서버가 켜질 때가 아니라 처음 쓸 때 GPU에 올라갑니다.

## API

로그인이 필요한 기능은 요청 머리에 `Authorization: Bearer <로그인 때 받은 토큰>`을 넣습니다.

| 주소 | 방식 | 로그인 | 하는 일 |
|---|---|---|---|
| /auth/register | POST | X | 회원가입 |
| /auth/login | POST | X | 로그인, 토큰 발급 |
| /extract | POST | O | 사진과 찍은 점(`[{"x","y","label"}]`)을 받아 SAM으로 윤곽 후보 만들기 |
| /extract/{번호}/refine | POST | O | 윤곽 다듬기 |
| /extract/{번호}/candidate/{순번} | GET | O | 후보 하나 보기 |
| /extract/{번호}/select | POST | O | 후보 확정 |
| /extract/{번호}/cutout | GET | O | 배경을 지운 객체 사진 |
| /composite | POST | O | 합성 작업을 줄에 세우고 작업 번호를 바로 돌려줌 |
| /job/{번호} | GET | O | 작업 상태 (queued / processing / done / failed) |
| /result/{번호} | GET | O | 합성 결과 사진 |
| /history | GET | O | 내 작업 기록 |
| /health | GET | X | 서버 상태 확인 |

## SAM과 SAM2

- 지금 코드의 상의 추출은 **SAM(1세대, vit_h)**이다(`pipeline.py`의 `_get_sam_predictor`, `extract_mask_candidates`). 이전 프로젝트에서 서지섭이 쓰던 것이다.
- 팀은 SAM2를 쓸 예정이라 이 부분을 SAM2로 바꿔야 한다.
- 주의: SAM2는 torch 2.5.1 이상이 필요한데(SAM2 공식 저장소 기준), 백엔드 본체는 AnyDoor 때문에 torch 2.0에 묶여 있어 같은 환경에 넣을 수 없다. PCTNet, BiRefNet처럼 별도 환경에서 따로 돌리고 표준입출력으로 주고받는 방식(`birefnet_client.py`, `birefnet_worker.py` 참고)으로 붙이면 된다. 서지섭 PC의 별도 환경 `venv_libcom`은 torch 2.6.0, torchvision 0.21.0이라 SAM2 조건을 만족한다.
- SAM2로 바꾸기 전까지 추출을 쓰려면 위 폴더 배치대로 SAM 1세대를 받아 둔다.

## 알아 둘 것

- **지금 `/composite`는 AnyDoor가 아니다.** 오려낸 객체를 그대로 붙인 뒤 색감만 맞추고 그림자를 넣는다(`pipeline.py`의 `composite_with_synthetic_shadow`). AnyDoor 합성 함수 `composite_anydoor`는 있지만 작업 줄(`queue_worker.py`)에 연결되어 있지 않다. 상의 합성에 쓰려면 이 연결을 바꿔야 한다.
- 합성은 한 번에 하나씩 처리한다(`queue_worker.py`). 여러 요청이 와도 순서대로 처리한다.
- 색감 보정(PCTNet)과 정밀 재분할(BiRefNet)은 torch 2.6이 필요해서 별도 파이썬 환경(`../venv_libcom`)에서 따로 돈다(`harmony_client.py`, `birefnet_client.py`). 그 환경이 없으면 이 두 단계는 건너뛰고 기본 방식으로 처리한다.
- `try_composite.py`: 서버, DB, 로그인 없이 합성 로직만 시험하는 개발용 도구.
- 비밀번호는 표준 라이브러리(pbkdf2)로 저장한다. 실제 서비스로 열 때는 HTTPS가 따로 필요하다.
