# AnyDoor 재학습 (B200 서버용)

## 1. 개요

- 목적: 기존 상의 잔존 유형 B 개선. 새 상의가 원래 상의보다 짧거나 소매가 없을 때, 남는 자리(배·팔·허리)에 엉뚱한 천이 생성되는 문제
- 방법: AnyDoor 모델 구조는 그대로 두고, VITON-HD 학습 재료만 바꿔 공식 가중치에서 이어서 학습 (미세 조정)
- 학습 재료 변경

| 구분 | 원래 AnyDoor | 재학습 |
|---|---|---|
| 생성 영역 (다시 그릴 자리) | 상의 라벨(`image-parse-v3` 5번) 박스 × 1.1~1.2 | 상체 + 팔 (`agnostic-mask` 모양 그대로) |
| 조건 이미지 (옷 그림) | 옷 사진 고주파 지도를 생성 영역 크기에 맞춰 늘림 | 생성 영역을 비우고, 고주파 지도를 옷 사진 비율 그대로 어깨 너비 기준 크기로 목부터 배치 |
| 거르기 | 마스크 연결성·면적 | 추가: 부위 지도 오류, 옷 사진 마스크 오류, 관절 점 없음 |

- 시험 결과 (2026-10-24 확인, RTX 3080 10GB, 100쌍 · 1,000스텝): VITON-HD 시험용 유형 B 5장 × seed 3개 모두 엉뚱한 천 없이 맨살 생성 (육안), 같은 입력에서 원래 가중치는 실패
- 이 문서: B200 서버에서 본 학습을 진행하는 순서

## 2. 파일 구성

| 파일 | 용도 |
|---|---|
| `retrain_dataset.py` | 학습 재료 (생성 영역·조건 이미지 생성, 거르기 기준, 옷 그림 배치 상수) |
| `retrain_ids.py` | 학습 쌍 목록 `ids.txt` 생성 (`test` = 시험 100쌍, `all` = 전체) |
| `retrain_train.py` | 학습 (GPU 개수, GPU당 사진 수, 스텝 수, 저장 간격 지정) |
| `retrain_compose_test.py` | 결과 확인 합성 (유형 B 5장 × seed 3개, 원래·재학습 가중치 비교) |
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
- 확인: `train_samples.jpg`에서 생성 영역(흰색) = 상체 + 팔, 조건 이미지에 옷 그림이 가슴~허리 위치

2. 동작 확인 (GPU 1개, 20스텝, 가중치 저장 안 함)

```bash
python retrain_train.py $HOME/retrain_run --steps 20 --gpus 1 --batch 1
```

- 확인: 스텝마다 `스텝 N: 초, 손실, GPU 최대 메모리` 출력, 오류 없음
- 참고 (RTX 3080 10GB): 스텝당 약 22초, GPU 최대 22.4GB (공유 GPU 메모리 사용)

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

- 스텝 수·저장 간격은 예시: 저장한 가중치를 [8. 결과 확인](#8-결과-확인-유형-b-5장) 방법으로 비교해 조정
- 저장: `$HOME/retrain_run/checkpoints/wide-step=2000.ckpt`, `wide-step=4000.ckpt`, … (1개 약 10GB)
- 접속이 끊겨도 계속 실행되도록 `nohup` 또는 `tmux` 사용

## 8. 결과 확인 (유형 B 5장)

- 서버 또는 기존 PC(가중치 파일 복사)에서 실행, 저장소 최상위의 `features/composition`(서버 합성 코드) 사용

```bash
python retrain_compose_test.py $HOME/retrain_run/compose original original
python retrain_compose_test.py $HOME/retrain_run/compose step2000 $HOME/retrain_run/checkpoints/wide-step=2000.ckpt
```

- 결과: `compose_compare.jpg` (원래 사진 / 새 상의 / 새 입력 / 원래 가중치 / 재학습 가중치, 첫 seed), 합성 사진 seed 3개씩
- 판정: 남는 자리(배·팔)에 엉뚱한 천 없이 맨살, 새 옷 무늬·모양 유지
- 비교 기준: 2026-10-24 시험 학습(100쌍 · 1,000스텝) 결과

## 9. 주의

- AnyDoor 공식 가중치 파일은 덮어쓰지 않음 (학습 결과는 결과 폴더에만 저장)
- VITON-HD 데이터와 학습 결과 가중치는 GitHub 업로드 금지
- 앱·서버 반영은 아직 아님: 새 입력에 필요한 상체 + 팔 영역과 관절 점을 앱 사진에서 만드는 방법 필요 (현재 학습·확인은 VITON-HD 제공 값 사용)
- 거르기 기준·옷 그림 배치 상수(`K_A` 0.93, `OFF` −0.25)는 `retrain_dataset.py` 맨 위
