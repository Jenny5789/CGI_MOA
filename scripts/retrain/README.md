# AnyDoor 재학습 (B200 서버용)

## 1. 개요

- 목적: 기존 상의 잔존 유형 B 개선. 새 상의가 원래 상의보다 짧거나 소매가 없을 때, 남는 자리(배·팔·허리)에 엉뚱한 천이 생성되는 문제
- 방법: AnyDoor 모델 구조는 그대로 두고, VITON-HD 학습 재료만 바꿔 공식 가중치에서 이어서 학습 (미세 조정)
- 학습 재료 변경

| 구분 | 원래 AnyDoor | 재학습 |
|---|---|---|
| 생성 영역 (다시 그릴 자리) | 상의 라벨(`image-parse-v3` 5번) 박스 × 1.1~1.2 | 상체 + 팔 + 원래 상의 (`agnostic-mask` + 상의 라벨 5번 5px 넓힘, 모양 그대로) |
| 조건 이미지 (옷 그림) | 옷 사진 고주파 지도를 생성 영역 크기에 맞춰 늘림 | 생성 영역을 비우고, 고주파 지도를 옷 사진 비율 그대로 어깨 너비 기준 크기로 목부터 배치 |
| 참조 이미지 (옷 사진) 증강 | 좌우 뒤집기 + 밝기·대비 무작위 (각 50%) | 밝기·대비 무작위만 (50%, 원래와 같은 설정), 좌우 뒤집기는 옷 그림 위치가 정답과 어긋나 제외 |
| 거르기 | 마스크 연결성·면적 | 추가: 부위 지도 오류, 옷 사진 마스크 오류, 관절 점 없음 |

- 시험 결과 (2026-10-24 확인, RTX 3080 10GB, 100쌍 · 1,000스텝): VITON-HD 시험용 유형 B 5장 × seed 3개 모두 엉뚱한 천 없이 맨살 생성 (육안), 같은 입력에서 원래 가중치는 실패
- 추가 확인 (2026-10-25, 위 가중치로 합성만): 생성 영역에 원래 상의를 더하면 VITON-HD 시험용 95장 중 원래 옷 조각이 남던 6장이 좋아지고 나빠진 사진 0장 (육안) → 학습 재료에 반영, 원래 AnyDoor에 있던 참조 이미지 밝기·대비 증강도 다시 넣음 (10/24 시험 학습 재료에는 둘 다 없음)
- 새 학습 재료 시험 학습 (2026-10-25, RTX 3080, 10/24와 같은 100쌍 · 1,000스텝): 10/24 가중치와 같은 생성 영역·seed로 VITON-HD 시험용 95장 비교 → 나아짐 3 · 비슷 83 · 나빠짐 9 (육안, 옷 색 바뀜 5 · 없던 물건 4)
  - 색 바뀜 원인은 미확인 (참조 이미지 밝기·대비 증강 때문인지, 학습할 때마다 생기는 우연한 차이인지 구분 못 함) → 본 학습 학습 재료 선택은 [7. 학습 순서](#7-학습-순서) 4 참고
  - 다시 그린 정사각형이 원본보다 어두워지는 현상은 두 학습 재료 모두 있음 (짧은 학습 때문으로 추정), 앱의 박스 선 보정(개선 포아송)을 붙이면 두 가중치 모두 정리됨
- 이 문서: B200 서버에서 본 학습을 진행하는 순서

## 2. 파일 구성

| 파일 | 용도 |
|---|---|
| `retrain_dataset.py` | 학습 재료 (생성 영역·조건 이미지 생성, 거르기 기준, 옷 그림 배치 상수) |
| `retrain_ids.py` | 학습 쌍 목록 `ids.txt` 생성 (`test` = 시험 100쌍, `all` = 전체) |
| `retrain_train.py` | 학습 (GPU 개수, GPU당 사진 수, 스텝 수, 저장 간격 지정) |
| `retrain_compose_test.py` | 결과 확인 합성 (유형 B 5장 × seed 3개, 원래·재학습 가중치 비교) |
| `retrain_compare_95.py` | 결과 확인 95장 (여러 가중치를 같은 입력·seed로 비교, 옷 색·없던 물건까지, 박스 선 보정 전후 숫자) |
| `pairs_95.json` | 95장 비교 쌍 목록 (VITON-HD 시험용 사진 이름·seed, 2026-10-17 시험과 같은 쌍) |
| `HANDOFF.md` | 기존 PC에서 B200으로 넘어올 때의 상태·이어서 할 일 |
| `test_env_packages.txt` | 시험 학습 환경 패키지 목록 (`pip freeze`, 참고용) |

## 3. 준비 사항

| 항목 | 받는 곳 | 크기 |
|---|---|---|
| AnyDoor 공식 코드 | `https://github.com/ali-vilab/AnyDoor` (시험 커밋 `44ca2b2`) | - |
| AnyDoor 가중치 `epoch=1-step=8687.ckpt` | AnyDoor 공식 README 안내 또는 기존 PC `AnyDoor/checkpoints` 복사 | 16GB |
| DINOv2 가중치 `dinov2_vitg14_pretrain.pth` | 같음 | 4.3GB |
| VITON-HD 학습용 `zalando-hd-resized/train` | VITON-HD 배포처 또는 기존 PC `AnyDoor/data` 복사 | 4.8GB |
| VITON-HD 시험용 `zalando-hd-resized/test` | 같음 (결과 확인용) | - |
| 이 폴더 | 저장소 `CGI_MOA` 브랜치 `cej-retrain`의 `scripts/retrain` | - |

- 디스크: 위 파일 약 25GB + 학습 가중치 1개당 약 10GB × 저장 횟수
- 폴더 배치 (아래 명령 기준)

```
$HOME/AnyDoor/                          AnyDoor 공식 코드
  checkpoints/epoch=1-step=8687.ckpt
  checkpoints/dinov2_vitg14_pretrain.pth
  data/zalando-hd-resized/train, test
$HOME/CGI_MOA/                          저장소 (브랜치 cej-retrain)
$HOME/retrain_run/                      학습 결과 폴더
```

```bash
git clone https://github.com/ali-vilab/AnyDoor.git $HOME/AnyDoor
git clone -b cej-retrain https://github.com/Jenny5789/CGI_MOA.git $HOME/CGI_MOA
```

## 4. 환경 구축

1. 가상환경 (Python 3.10)

```bash
python3.10 -m venv $HOME/venv-anydoor
source $HOME/venv-anydoor/bin/activate
```

2. PyTorch: B200은 CUDA 12.8 이상을 지원하는 PyTorch 필요 (공개 정보 기준, `nvidia-smi`로 드라이버·CUDA 버전 확인 후 설치)

```bash
nvidia-smi
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

3. 나머지 패키지

```bash
pip install pytorch-lightning==1.9.5 omegaconf einops albumentations==1.3.0 opencv-python timm transformers fvcore safetensors scipy numpy Pillow
```

- 시험 환경 버전: Python 3.10, torch 2.5.1+cu121, pytorch-lightning 1.9.5, transformers 5.14.1, timm 1.0.28, albumentations 1.3.0, numpy 2.2.6, omegaconf 2.3.1 (전체 목록 `test_env_packages.txt`)
- 패키지 버전 충돌 시 `test_env_packages.txt`의 버전 우선 (torch는 B200 지원 버전 유지)

4. GPU 확인

```bash
python -c "import torch; print(torch.__version__, torch.cuda.device_count(), torch.cuda.get_device_name(0))"
```

- 판정: GPU 개수와 B200 이름 출력, 오류 없음

## 5. AnyDoor 코드 설정

1. `ldm/models/diffusion/ddpm.py`: pytorch-lightning 1.9 호출 방식에 맞춤 (한 줄)

```bash
cd $HOME/AnyDoor
sed -i 's/def on_train_batch_start(self, batch, batch_idx, dataloader_idx):/def on_train_batch_start(self, batch, batch_idx, dataloader_idx=0):/' ldm/models/diffusion/ddpm.py
```

2. `configs/anydoor.yaml`: DINOv2 가중치 경로 (공식 기본값 `path/dinov2_vitg14_pretrain.pth`)

```bash
sed -i "s#weight: path/dinov2_vitg14_pretrain.pth#weight: $HOME/AnyDoor/checkpoints/dinov2_vitg14_pretrain.pth#" configs/anydoor.yaml
```

3. `configs/inference.yaml`: 결과 확인 합성([8. 결과 확인](#8-결과-확인-유형-b-5장))을 서버에서 할 때만, AnyDoor 가중치 경로 (공식 기본값 `path/epoch=1-step=8687.ckpt`)

```bash
sed -i "s#pretrained_model: path/epoch=1-step=8687.ckpt#pretrained_model: $HOME/AnyDoor/checkpoints/epoch=1-step=8687.ckpt#" configs/inference.yaml
```

- 확인

```bash
grep -n "dataloader_idx=0" ldm/models/diffusion/ddpm.py
grep -n "weight:" configs/anydoor.yaml
```

## 6. 경로 설정

```bash
export ANYDOOR_DIR=$HOME/AnyDoor
export VITON_TRAIN_DIR=$ANYDOOR_DIR/data/zalando-hd-resized/train
export VITON_TEST_DIR=$ANYDOOR_DIR/data/zalando-hd-resized/test
cd $HOME/CGI_MOA/scripts/retrain
```

- 새 터미널마다 다시 설정 (또는 `~/.bashrc`에 추가)

## 7. 학습 순서

1. 학습 쌍 목록 (CPU)

```bash
python retrain_ids.py $HOME/retrain_run all --samples
```

- 결과: `$HOME/retrain_run/ids.txt` (쓸 수 있는 쌍, 시험 3,000쌍 기준 약 94%), `train_samples.jpg`
- 확인: `train_samples.jpg`에서 생성 영역(흰색) = 상체 + 팔 + 원래 상의, 조건 이미지에 옷 그림이 가슴~허리 위치

2. 동작 확인 (GPU 1개, 20스텝, 가중치 저장 안 함)

```bash
python retrain_train.py $HOME/retrain_run --steps 20 --gpus 1 --batch 1
```

- 확인: 스텝마다 `스텝 N: 초, 손실, GPU 최대 메모리` 출력, 오류 없음
- 참고 (RTX 3080 10GB): 스텝당 약 22초, GPU 최대 22.4GB (공유 GPU 메모리 사용)
- 시작할 때 `학습 재료: 생성 영역에 원래 상의 포함, 참조 이미지 밝기·대비 무작위 함` 출력 (기본)
- 학습 재료를 2026-10-24 시험과 같게 하려면 `--no-wide-top --no-ref-aug` 추가

3. 여러 GPU 확인 (20스텝, 가중치 저장 안 함)

```bash
python retrain_train.py $HOME/retrain_run --steps 20 --gpus 8 --batch 4
```

- `--gpus`: 서버 GPU 개수, `--batch`: GPU당 사진 수 (GPU 최대 메모리를 보며 조절)
- 한 스텝에 학습하는 사진 수 = GPU 개수 × batch (원래 AnyDoor 학습: GPU 2개 × 16장)

4. 본 학습

```bash
nohup python retrain_train.py $HOME/retrain_run --steps 10000 --gpus 8 --batch 4 --save-every 2000 > $HOME/retrain_run/train_log.txt 2>&1 &
tail -f $HOME/retrain_run/train_log.txt
```

- 학습 재료 선택: 기본 = 원래 상의 포함 + 참조 이미지 밝기·대비 증강
  - 2026-10-25 짧은 시험 학습에서 옷 색 바뀜이 늘었음 (원인 미확인, [1. 개요](#1-개요) 참고) → 밝기·대비 증강을 끄려면 `--no-ref-aug` 추가

```bash
nohup python retrain_train.py $HOME/retrain_run_noaug --steps 10000 --gpus 8 --batch 4 --save-every 2000 --no-ref-aug > $HOME/retrain_run_noaug/train_log.txt 2>&1 &
```

  - 두 가지를 모두 학습할 경우 결과 폴더를 다르게 하고 (`ids.txt` 복사), [8. 결과 확인](#8-결과-확인-유형-b-5장) 방법으로 같은 스텝끼리 비교 (옷 색이 옷 사진과 같은지 함께 확인)
- 스텝 수·저장 간격은 예시: 저장한 가중치를 [8. 결과 확인](#8-결과-확인-유형-b-5장) 방법으로 비교해 조정
- 저장: `$HOME/retrain_run/checkpoints/wide-step=2000.ckpt`, `wide-step=4000.ckpt`, … (1개 약 10GB)
- 접속이 끊겨도 계속 실행되도록 `nohup` 또는 `tmux` 사용

## 8. 결과 확인 (유형 B 5장)

- 서버 또는 기존 PC(가중치 파일 복사)에서 실행, 저장소 최상위의 `features/composition`(서버 합성 코드) 사용

```bash
python retrain_compose_test.py $HOME/retrain_run/compose original original
python retrain_compose_test.py $HOME/retrain_run/compose step2000 $HOME/retrain_run/checkpoints/wide-step=2000.ckpt
```

- 생성 영역 기본 = 상체 + 팔 + 원래 상의 (학습 재료와 같음), 상체 + 팔만으로 비교하려면 끝에 `ag` (이름은 다르게, 예: `step2000_ag`)
- 결과: `compose_compare.jpg` (원래 사진 / 새 상의 / 새 입력 / 원래 가중치 / 재학습 가중치, 첫 seed), 합성 사진 seed 3개씩
- 판정: 남는 자리(배·팔)에 엉뚱한 천 없이 맨살, 새 옷 무늬·모양 유지
- 비교 기준: 2026-10-24 시험 학습(100쌍 · 1,000스텝) 결과

### 95장 비교 (옷 색·없던 물건까지)

- 유형 B 5장만으로는 옷 색 바뀜·없던 물건을 보기 어려움 → 95장으로 가중치 비교
- 처음에는 `--limit 2`로 동작 확인 (앞의 2쌍만, 오류 없이 `compare/V01.jpg`, `compare/V02.jpg`가 생기는지)

```bash
python retrain_compare_95.py $HOME/compare95 original=original aug10000=$HOME/retrain_run/checkpoints/wide-step=10000.ckpt noaug10000=$HOME/retrain_run_noaug/checkpoints/wide-step=10000.ckpt --limit 2
python retrain_compare_95.py $HOME/compare95 original=original aug10000=$HOME/retrain_run/checkpoints/wide-step=10000.ckpt noaug10000=$HOME/retrain_run_noaug/checkpoints/wide-step=10000.ckpt
```

- 가중치는 `이름=경로` (경로가 `original`이면 공식 가중치), 이미 만든 결과는 건너뜀 (두 번째 명령은 나머지 93쌍만 합성)
- 결과: `overview_?.jpg` (12쌍씩, 원래 사진 | 입힐 옷 | 가중치별 결과), `compare/V??.jpg` (한 쌍씩, 포아송 붙인 결과 포함), `compare_95.csv` (박스 선 세기 포아송 전·후, 밝기 변화)
- 판정할 사진을 고른 뒤 `--pick V02,V08,V10`을 붙여 다시 실행하면 `compare_pick.jpg` (합성은 건너뛰고 그림만 다시 만듦)
- 참고 (기존 PC 2026-10-25, 1,000스텝): 새 학습 재료 가중치에서 옷 색 바뀜 V10·V29·V56·V90·V53, 없던 물건 V02·V08·V38·V68

## 9. 주의

- AnyDoor 공식 가중치 파일은 덮어쓰지 않음 (학습 결과는 결과 폴더에만 저장)
- VITON-HD 데이터와 학습 결과 가중치는 GitHub 업로드 금지
- 앱·서버 반영은 아직 아님: 새 입력에 필요한 상체 + 팔 영역과 관절 점을 앱 사진에서 만드는 방법 필요 (현재 학습·확인은 VITON-HD 제공 값 사용)
- 거르기 기준·옷 그림 배치 상수(`K_A` 0.93, `OFF` −0.25)·원래 상의 넓힘(`DIL` 5px)·참조 이미지 증강(`REF_AUG`)은 `retrain_dataset.py` 맨 위
