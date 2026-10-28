# AnyDoor 재학습 인수인계 (B200 컴퓨터로 이동)

- 작성: 2026-10-26 (기존 PC → B200 컴퓨터)
- 실행 방법은 같은 폴더 [README.md](README.md), 이 문서는 지금까지의 상태와 이어서 할 일
- 기존 PC 없이 B200만으로 진행: 필요한 것 = GitHub 브랜치 `cej-retrain` (코드·문서·95장 쌍 목록) + [2장](#2-가져갈-파일-github-업로드-금지-외장-드라이브-등으로-직접-복사)의 큰 파일 4개
- 작업일지: GitHub `main`의 `docs/작업일지.md` 하나 (두 컴퓨터 공용, B200에서 쓴 날짜·항목은 `[B200]` 표시, 맨 위 "작성 컴퓨터 구분" 참고, 10/28 `dev-cej` 브랜치 삭제)

```bash
git clone -b main https://github.com/Jenny5789/CGI_MOA.git $HOME/CGI_MOA_dev   # 작업일지: $HOME/CGI_MOA_dev/docs/작업일지.md (이미 dev-cej로 받아 둔 폴더는 main으로 바꾸기)
```

## 1. 목적과 지금 상태

- 목적: 기존 상의 잔존 유형 B 개선 (새 상의가 짧거나 소매가 없을 때 남는 자리에 엉뚱한 천이 생기는 문제)
- 방법: **AnyDoor 기반 유지** (모델 교체 안 함), 학습 재료(문제지)만 바꿔 공식 가중치에서 이어서 학습
- 지금까지 (기존 PC, RTX 3080, 100쌍 · 1,000스텝 시험)

| 날짜 | 한 일 | 결과 |
|---|---|---|
| 10/24 | 새 입력(상체 + 팔 영역, 옷 그림 어깨 기준 배치)으로 시험 학습 | 유형 B 5장 × seed 3 모두 엉뚱한 천 사라짐 |
| 10/25 | 95장 확인 | 좋아짐 20 · 비슷 67 · 나빠짐 6 |
| 10/25 | 그릴 때 영역에 원래 상의 더하기 | 원래 옷 조각 남던 6장 좋아짐, 나빠짐 0 |
| 10/25 | 다시 그린 정사각형이 어두워지는 원인 | 재학습 때문 (학습 재료 실수는 아님), 앱의 박스 선 보정(포아송)으로 정리됨 |
| 10/25 | 학습 재료 수정 (원래 상의 포함 + 옷 사진 밝기·대비 증강) → 같은 조건 1,000스텝 | 10/24 대비 나아짐 3 · 비슷 83 · 나빠짐 9 (옷 색 바뀜 5, 없던 물건 4), 원인 미확인 |

- 정하지 못한 것: 옷 사진 밝기·대비 증강을 넣을지 → **B200에서 두 가지 모두 학습해 비교** (추천)
  - 기본: 원래 상의 포함 + 밝기·대비 증강
  - `--no-ref-aug`: 원래 상의 포함만

## 2. 가져갈 파일 (GitHub 업로드 금지, 외장 드라이브 등으로 직접 복사)

| 파일 | 기존 PC 위치 | 크기 |
|---|---|---|
| AnyDoor 공식 가중치 `epoch=1-step=8687.ckpt` | `Desktop\AnyDoor\checkpoints\` | 16.8GB |
| DINOv2 가중치 `dinov2_vitg14_pretrain.pth` | 같은 폴더 | 4.5GB |
| VITON-HD 학습용 `train` (11,647장) | `Desktop\AnyDoor\data\zalando-hd-resized\train` | 4.8GB |
| VITON-HD 시험용 `test` (2,032장) | 같은 폴더의 `test` | 0.8GB |

- 코드는 B200에서 GitHub으로 받음: AnyDoor 공식 (`ali-vilab/AnyDoor`, 커밋 `44ca2b2`), 이 저장소 브랜치 `cej-retrain`
- B200 디스크: 위 약 27GB + 가중치 1개 약 10GB × 저장 횟수 × 학습 종류 수

## 3. B200에서 할 순서 (README 장 번호)

1. 환경 확인: 운영체제, GPU 개수, `nvidia-smi` (CUDA 12.8 이상 지원 드라이버), 디스크, 인터넷
2. 환경 구축 (4장), AnyDoor 코드 설정 (5장, 한 줄 수정 + 경로 2곳), 경로 설정 (6장)
3. 학습 쌍 목록 `retrain_ids.py ... all --samples` (7장 1) → `train_samples.jpg`에서 흰색 영역 = 상체 + 팔 + 원래 상의 확인
4. 동작 확인 20스텝 (GPU 1개) → 여러 GPU 20스텝 (7장 2·3), `--batch`는 GPU 메모리를 보며 조절
5. 본 학습 두 가지 (7장 4), 결과 폴더를 다르게, `ids.txt` 복사

```bash
mkdir -p $HOME/retrain_run_noaug && cp $HOME/retrain_run/ids.txt $HOME/retrain_run_noaug/
nohup python retrain_train.py $HOME/retrain_run --steps 10000 --gpus 8 --batch 4 --save-every 2000 > $HOME/retrain_run/train_log.txt 2>&1 &
# 앞의 학습이 끝난 뒤 (GPU를 나눠 쓰지 않을 때)
nohup python retrain_train.py $HOME/retrain_run_noaug --steps 10000 --gpus 8 --batch 4 --save-every 2000 --no-ref-aug > $HOME/retrain_run_noaug/train_log.txt 2>&1 &
```

- 시작할 때 출력되는 `학습 재료: ...` 줄로 설정 확인
- 스텝 수·GPU 수·batch는 예시 (기존 PC 시험은 GPU 1개 × 1장 × 1,000스텝)

6. 결과 확인 합성 (8장): 원래 가중치 + 저장 스텝별 두 가지, 이름을 다르게

```bash
python retrain_compose_test.py $HOME/compose original original
python retrain_compose_test.py $HOME/compose aug_step10000 $HOME/retrain_run/checkpoints/wide-step=10000.ckpt
python retrain_compose_test.py $HOME/compose noaug_step10000 $HOME/retrain_run_noaug/checkpoints/wide-step=10000.ckpt
```

7. 95장 비교 (README 8장 "95장 비교"): 먼저 `--limit 2`로 동작 확인 → 95장 → 사진 고른 뒤 `--pick`

```bash
python retrain_compare_95.py $HOME/compare95 original=original aug10000=$HOME/retrain_run/checkpoints/wide-step=10000.ckpt noaug10000=$HOME/retrain_run_noaug/checkpoints/wide-step=10000.ckpt --limit 2
```

## 4. 결과 판정 기준

- 유형 B 5장 (`compose_compare.jpg`): 남는 자리(배·팔)에 엉뚱한 천 없이 맨살, 원래 옷 조각 없음, 새 옷 무늬·모양 유지
- 옷 색: 옷 사진과 같은 색인지 (10/25 시험에서 회색 → 초록, 남색 → 청록, 연노랑 → 분홍 같은 색 바뀜)
- 없던 물건: 벨트·얼룩·레이스 층, 바지 색 바뀜
- 다시 그린 정사각형 경계(박스 선)·어두워짐: 앱에서 박스 선 보정이 붙으므로 판정에서 제외 가능
- `retrain_compose_test.py`는 유형 B 5장만 → 옷 색·없던 물건은 `retrain_compare_95.py`로 95장 비교 (3장 7)
  - 10/25 시험에서 문제였던 사진: 옷 색 V10·V29·V56·V90·V53, 없던 물건 V02·V08·V38·V68 (이 사진들을 먼저 확인)
  - `retrain_compare_95.py`는 기존 PC의 비교 스크립트를 B200용(리눅스 경로·여러 가중치)으로 옮긴 것, 기존 PC에서는 실행하지 않음 → B200에서 `--limit 2`로 먼저 확인

## 5. 결과 가져오기

- 가져올 것: `train_log.txt` (두 가지), `compose_compare.jpg`, 95장 비교 `overview_?.jpg`·`compare_pick.jpg`·`compare_95.csv`, 고른 가중치만 (1개 약 10GB, 외장 드라이브)
- GitHub에는 그림·기록 문서만 (가중치·VITON-HD 금지)

## 6. 지킬 것

- AnyDoor 기반 유지: 다른 모델은 보완으로만, 새 모델·도구를 쓰기 전에 사용자 확인
- GitHub 업로드 금지: VITON-HD, Dress Code, 학습 가중치
- AnyDoor 공식 가중치 덮어쓰지 않기 (학습 결과는 결과 폴더에만)
- push 전 열린 PR 확인, 강제 push 금지
- 커밋은 결과를 사용자가 확인한 뒤

## 7. 기존 PC 상태 (돌아왔을 때)

- `CGI_V2`: `dev-cej` = `main` (10/28 `b30728b`, GitHub `dev-cej`는 10/28 삭제), 앱 코드 변경 없음
- `cej-retrain`: GitHub 최신 (README에 10/25 결과·`--no-ref-aug` 안내·95장 비교, 95장 비교 스크립트·쌍 목록, 이 문서)
- 작업일지: `docs/작업일지.md`로 옮김 (2026-10-26 `dev-cej`, 10/28부터 `main`), 기존 PC `CGI_MOA`의 작업일지는 10/26 ③까지 기록하고 더 쓰지 않음
- 시험 결과 (`Desktop\anydoor_retrain_test\`): 10/24 가중치 `checkpoints\`, 10/25 가중치 `run_1025\checkpoints\`, 비교 `compare_1025\` 등

## 8. 새 컴퓨터에서 Claude와 작업할 때

- 답변은 한국어, 쉬운 말 (모르는 용어는 비유로)
- 고치기 전에 파일·위치·전→후·이유를 먼저 설명, 한 단계씩
- 원인은 "확인"과 "추정"을 나눠 적기, 모델 탓으로 보기 전에 확대해 보고 seed 여러 개로 확인
- 시험 기록은 작업일지(`main`의 `docs/작업일지.md`)에 `[합성 test]` 표시, B200에서 쓴 날짜·항목은 `[B200]` 표시
- 작업일지는 두 컴퓨터에서 동시에 고치지 않기: 쓰기 전에 `main` pull, 쓴 뒤 커밋·push → PR로 `main`에 합치기 (커밋·push는 결과 확인 뒤 사용자 요청 시)
- 그림은 칸 이름·설명을 쉬운 말로, 원래 사진과 입힐 옷을 나란히
