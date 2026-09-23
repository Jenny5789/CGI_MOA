# SAM2 사람 추출 테스트

- 최초 실험일: 2026-09-22
- 추가 실험일: 2026-09-23
- 실험 단계: 사람 추출 / SAM2 Point Prompt 테스트
- 실행 도구: ComfyUI


## 1. 테스트 목적

MOA의 사람 이미지 추출 기능에 SAM2를 적용하고,
실제 사람 이미지에서 Positive Point의 개수와 위치에 따라
사람 영역 Mask가 어떻게 생성되는지 확인한다.

현재 테스트에서는 다음 3개의 사람 이미지를 사용하였다.

- `Girl.jpg`
- `Standing_man.jpg`
- `Bent_man.jpg`

각 이미지에서 Positive Point를 1개, 2개, 3개로 증가시키며
Mask 결과의 변화를 확인하였다.

`Bent_man` 테스트에서는 BiRefNet과 SAM2의 비교 조건을 통제하기 위해
동일한 크기의 입력 이미지를 두 모델에 사용하였다.


## 2. 사용 모델 및 실행 환경

- 모델: SAM2
- 모델 파일: `sam2_hiera_base_plus.safetensors`
- Segmentor: `single_image`
- Device: `cuda`
- Precision: `fp16`
- 실행 도구: ComfyUI

사용한 ComfyUI Custom Node:

- `ComfyUI-segment-anything-2`
- `ComfyUI-KJNodes`

SAM2 모델은 `(Down)Load SAM2Model` 노드로 불러왔다.

Point 입력에는 KJNodes의 `Points Editor`를 사용하였다.

사용 GPU:

- NVIDIA GeForce RTX 3080
- VRAM 10 GB

현재 테스트에서는 Peak VRAM을 별도로 측정하지 않았다.

- Peak VRAM: 미측정


## 3. 실행 Workflow

실제 구성한 흐름은 다음과 같다.

`Load Image`

→ `Points Editor`

→ `Sam2Segmentation`

→ `Mask to Image`

→ `Preview Image`

→ `Save Image`

이미지는 `Sam2Segmentation`의 `image`로 전달하였다.

`Points Editor`에서 지정한 Positive Point는
`Sam2Segmentation`의 `coordinates_positive`로 전달하였다.

SAM2가 출력한 `mask`는 `Mask to Image`를 거쳐
이미지로 변환한 뒤 확인 및 저장하였다.


# 테스트 01 — Girl


## 4. 입력 이미지

- 실험일: 2026-09-22
- 파일명: `Girl.jpg`
- 이미지 크기: 975 × 1463

입력 위치:

`experiments/object_extraction/001_person_extraction/inputs/Girl.jpg`


## 5. Girl — Point별 실행 결과

### Positive Point 1개

조건:

- Positive Point: 1개
- 위치: 바지 내부

결과:

- 사람 전체가 아닌 의복 중심 영역이 Mask로 생성되었다.
- 이번 입력 이미지에서는 Positive Point 1개만으로 사람 전체 영역을 얻지 못했다.

저장 파일:

`Girl_SAM2_point1_mask_00001_.png`

실행 로그:

`combined labels: [1.]`

`combined labels shape: (1,)`

`Processing Images: 1.30 s/it`

`Prompt executed in 4.05 seconds`


### Positive Point 2개

조건:

- Positive Point: 2개
- 위치: 바지 + 상체

결과:

- 1-Point보다 사람 전체에 가까운 영역으로 Mask가 크게 확장되었다.
- 머리부터 다리까지 주요 인체 영역이 포함되었다.
- 일부 영역에 작은 누락 및 구멍이 관찰되었다.
- 사람 주변 구조물 일부도 Mask에 포함되었다.

저장 파일:

`Girl_SAM2_point2_mask_00001_.png`

실행 로그:

`combined labels: [1. 1.]`

`combined labels shape: (2,)`

`Processing Images: 2.27 it/s`

`Prompt executed in 1.17 seconds`


### Positive Point 3개

조건:

- Positive Point: 3개
- 위치: 바지 + 상체 + 얼굴

결과:

- 사람 전체에 가까운 Mask가 생성되었다.
- 2-Point 결과와 육안상 전체적인 형태가 비슷하게 나타났다.
- 세 번째 Point를 추가했지만 눈에 띄는 큰 변화는 확인하지 못했다.

저장 파일:

`Girl_SAM2_point3_mask_00001_.png`

실행 로그:

`combined labels: [1. 1. 1.]`

`combined labels shape: (3,)`

`Processing Images: 1.91 it/s`

`Prompt executed in 1.10 seconds`


# 테스트 02 — StandingMan


## 6. 입력 이미지 및 크기 조정

- 실험일: 2026-09-22
- 원본 파일명: `Standing_man.jpg`
- 원본 이미지 크기: 3000 × 5332

원본 위치:

`experiments/object_extraction/001_person_extraction/inputs/Standing_man.jpg`

원본 이미지를 Points Editor에 입력하는 과정에서 다음 오류가 발생하였다.

`Value 5332 bigger than max of 4096: height`

현재 사용한 Points Editor의 최대 height가 4096이었기 때문에
원본 이미지의 높이 5332를 그대로 사용할 수 없었다.

처음에는 ComfyUI의 Image Scale 노드를 사용하여
축소된 이미지를 Points Editor에 전달하려 하였으나,
해당 구성에서는 Points Editor 캔버스에 이미지가 정상적으로 표시되지 않았다.

따라서 원본 이미지는 보존하고
가로세로 비율을 유지한 SAM2 실험용 이미지를 별도로 생성하였다.

SAM2 입력 이미지:

- 파일명: `Standingman_2305x4096.jpg`
- 이미지 크기: 2305 × 4096

저장 위치:

`experiments/object_extraction/001_person_extraction/inputs/Standingman_2305x4096.jpg`

StandingMan 테스트에서는 SAM2에 위 축소 이미지를 사용하였다.


## 7. StandingMan — Point별 실행 결과

### Positive Point 1개

조건:

- Positive Point: 1개
- 위치: 몸통 중앙

결과:

- 상의 및 상체 중심의 영역이 Mask로 생성되었다.
- 머리와 얼굴은 Mask에서 제외되었다.
- 하체와 신발도 Mask에서 제외되었다.
- 사람 전체 영역은 생성되지 않았다.

저장 파일:

`Standingman_SAM2_point1_mask_00001_.png`

실행 로그:

`combined labels: [1.]`

`combined labels shape: (1,)`

`Processing Images: 1/1 [00:00<00:00, 1.62it/s]`

`Prompt executed in 3.61 seconds`


### Positive Point 2개

조건:

- Positive Point: 2개
- 위치: 몸통 + 허벅지

결과:

- 머리부터 신발까지 사람 전체 영역이 Mask에 포함되었다.
- 몸통과 다리가 하나의 연결된 영역으로 생성되었다.
- 두 다리 사이의 배경이 대부분 분리되었다.
- 목 부근에 작은 내부 누락이 관찰되었다.
- 신발 주변에 작은 불규칙 영역이 관찰되었다.
- 현재 육안 확인 범위에서는 큰 주변 구조물이 Mask에 포함된 모습은 보이지 않았다.

저장 파일:

`Standingman_SAM2_point2_mask_00001_.png`

실행 로그:

`combined labels: [1. 1.]`

`combined labels shape: (2,)`

`Processing Images: 1/1 [00:00<00:00, 1.87it/s]`

`Prompt executed in 1.85 seconds`


### Positive Point 3개

조건:

- Positive Point: 3개
- 위치: 몸통 + 허벅지 + 얼굴

결과:

- 머리부터 신발까지 사람 전체 영역이 Mask에 포함되었다.
- 전체적인 실루엣은 2-Point 결과와 육안상 유사하였다.
- 2-Point에서 보였던 목 부근의 작은 누락은 육안상 줄어든 것으로 보였다.
- 신발 주변의 작은 불규칙 영역은 여전히 관찰되었다.
- 세 번째 Point를 추가했지만 전체 Mask 형태의 큰 변화는 관찰되지 않았다.

저장 파일:

`Standingman_SAM2_point3_mask_00001_.png`

실행 로그:

`combined labels: [1. 1. 1.]`

`combined labels shape: (3,)`

`Processing Images: 1/1 [00:00<00:00, 1.87it/s]`

`Prompt executed in 2.01 seconds`

Workflow:

`Standingman_SAM2_workflow.json`


# 테스트 03 — BentMan


## 8. 입력 이미지 및 동일 조건 구성

- 실험일: 2026-09-23
- 원본 파일명: `Bent_man.jpg`
- 원본 이미지 크기: 3536 × 5304

원본 위치:

`experiments/object_extraction/001_person_extraction/inputs/Bent_man.jpg`

원본 이미지의 높이가 Points Editor의 최대 height 4096을 초과하기 때문에
가로세로 비율을 유지한 공통 실험 이미지를 생성하였다.

공통 실험 이미지:

- 파일명: `Bent_man_2791x4096.jpg`
- 이미지 크기: 2791 × 4096

저장 위치:

`experiments/object_extraction/001_person_extraction/inputs/Bent_man_2791x4096.jpg`

이번 테스트에서는 BiRefNet과 SAM2 모두
동일한 `Bent_man_2791x4096.jpg`를 입력으로 사용하였다.

이를 통해 두 모델의 입력 이미지 해상도 차이를 제거한 상태에서
결과를 비교할 수 있도록 실험 조건을 구성하였다.


## 9. BentMan — Positive Point 1개

조건:

- Positive Point: 1개
- 위치: 몸통 중앙

결과:

- 사람 전체가 아닌 몸통 및 상의 주변 영역이 주로 선택되었다.
- 팔 일부 영역도 Mask에 포함되었다.
- 머리 전체는 포함되지 않았다.
- 바지, 다리와 신발은 대부분 제외되었다.
- 작은 분리 영역도 일부 관찰되었다.

따라서 이번 이미지에서도 Positive Point 1개만으로는
사람 전체 Mask를 얻지 못했다.

저장 파일:

`Bent_man_SAM2_point1_mask_00001_.png`

실행 로그:

`combined labels: [1.]`

`combined labels shape: (1,)`

`Processing Images: 1/1 [00:01<00:00, 1.36s/it]`

`Prompt executed in 4.53 seconds`


## 10. BentMan — Positive Point 2개

조건:

- Positive Point: 2개
- 위치: 몸통 + 허벅지

결과:

- 1-Point 결과와 비교하여 Mask가 사람 전체 영역으로 크게 확장되었다.
- 머리부터 신발까지 사람 전체 형태가 포함되었다.
- 뒤로 뻗은 양팔도 사람 영역에 포함되었다.
- 몸통, 팔, 하체가 하나의 사람 영역으로 연결되었다.
- 몸통 및 허리 주변에 작은 내부 누락 영역이 관찰되었다.
- 손 및 손목 주변에도 일부 불규칙한 영역이 관찰되었다.
- 신발 주변에도 작은 불규칙 영역이 관찰되었다.

저장 파일:

`Bent_man_SAM2_point2_mask_00001_.png`

실행 로그:

`combined labels: [1. 1.]`

`combined labels shape: (2,)`

`Processing Images: 1/1 [00:00<00:00, 1.61it/s]`

`Prompt executed in 2.27 seconds`


## 11. BentMan — Positive Point 3개

조건:

- Positive Point: 3개
- 위치: 몸통 + 허벅지 + 머리

결과:

- 머리부터 신발까지 사람 전체 영역이 Mask에 포함되었다.
- 몸통, 팔과 하체가 연결된 사람 영역으로 나타났다.
- 전체적인 Mask 형태는 2-Point 결과와 육안상 매우 유사하였다.
- 몸통 및 허리 주변의 작은 내부 누락은 여전히 관찰되었다.
- 손 및 손목 주변의 일부 불규칙 영역도 남아 있었다.
- 세 번째 Point를 추가했지만 2-Point 결과 대비 전체적인 형태의 큰 변화는 관찰되지 않았다.

저장 파일:

`Bent_man_SAM2_point3_mask_00001_.png`

실행 로그:

`combined labels: [1. 1. 1.]`

`combined labels shape: (3,)`

`Processing Images: 1/1 [00:00<00:00, 1.44it/s]`

`Prompt executed in 2.24 seconds`

Workflow:

`Bent_man_SAM2_workflow.json`


## 12. BentMan Point 개수에 따른 변화

| 조건 | 육안 관찰 결과 |
|---|---|
| Positive Point 1개 | 몸통 및 팔 일부 중심으로 선택되었으며 사람 전체는 생성되지 않음 |
| Positive Point 2개 | 머리부터 신발까지 사람 전체에 가까운 Mask로 확장 |
| Positive Point 3개 | 2-Point와 전체적인 형태가 유사하며 큰 변화는 관찰되지 않음 |

이번 `Bent_man` 이미지에서는
몸통의 Positive Point 1개만으로 사람 전체 Mask를 얻지 못하였다.

몸통과 허벅지에 Positive Point를 2개 사용했을 때
사람 전체에 가까운 Mask가 생성되었다.

세 번째 Point를 머리에 추가했지만
2-Point 결과와 비교하여 전체적인 Mask 형태의 큰 변화는 관찰되지 않았다.


## 13. 세 이미지의 Point 결과 누적 관찰

현재까지 테스트한 이미지:

1. `Girl.jpg`
2. `Standing_man.jpg`
3. `Bent_man.jpg`

세 이미지에서 관찰된 결과는 다음과 같다.

| 이미지 | 1-Point | 2-Point | 3-Point |
|---|---|---|---|
| Girl | 의복 중심 영역 | 사람 전체에 가까운 영역 | 2-Point와 전체 형태 유사 |
| StandingMan | 상체 중심 영역 | 사람 전체 영역 | 2-Point와 전체 형태 유사 |
| BentMan | 몸통/팔 일부 | 사람 전체에 가까운 영역 | 2-Point와 전체 형태 유사 |

현재 테스트한 세 이미지에서는
Positive Point 1개를 사용했을 때 사람 전체 영역이 생성되지 않았다.

Positive Point를 2개 사용했을 때는
세 이미지 모두 사람 전체에 가까운 영역으로 Mask가 확장되었다.

Positive Point를 3개로 증가시켰을 때는
세 이미지 모두 2-Point 결과 대비 전체적인 Mask 형태의 큰 변화가
육안상 관찰되지 않았다.

위 내용은 현재 테스트한 세 이미지에서 관찰한 결과이며,
SAM2의 일반적인 성능 특성으로 확정하지 않는다.


## 14. 실행 시간 기록 시 주의

현재 기록한 모든 `Prompt executed` 값은
ComfyUI Workflow 전체 실행 로그이다.

첫 번째 실행과 이후 실행에서는
모델 로딩 및 캐싱 상태가 동일하지 않을 수 있다.

따라서 다음 값을 SAM2의 순수 추론 시간이나
평균 추론 시간으로 사용하지 않는다.

### Girl

- 1-Point: 4.05 seconds
- 2-Point: 1.17 seconds
- 3-Point: 1.10 seconds

### StandingMan

- 1-Point: 3.61 seconds
- 2-Point: 1.85 seconds
- 3-Point: 2.01 seconds

### BentMan

- 1-Point: 4.53 seconds
- 2-Point: 2.27 seconds
- 3-Point: 2.24 seconds

현재 단계에서는 실행 당시의 원본 로그 값으로만 보존한다.


## 15. 현재 단계에서 판단하지 않은 내용

현재 테스트에서는 정답 Mask(Ground Truth)와 비교하지 않았다.

따라서 다음 항목은 아직 판단하지 않는다.

- IoU
- Dice
- 정량적인 추출 정확도
- BiRefNet 대비 성능 우열
- 평균 추론 시간
- Peak VRAM 비교
- SAM2의 일반적인 사람 추출 성능
- 모든 이미지에서 2-Point가 최적이라는 결론

현재까지 확인한 것은
SAM2가 ComfyUI에서 정상적으로 실행되며,
Positive Point의 위치와 개수에 따라 사람 영역 Mask가 달라질 수 있다는 것이다.

또한 현재 테스트한 세 이미지에서는
1-Point와 2-Point 사이에서 사람 영역의 범위가 크게 달라지는 현상이
반복적으로 관찰되었다.


## 16. 현재 테스트 상태

- [x] SAM2 모델 준비
- [x] ComfyUI에서 모델 인식
- [x] `Girl.jpg` 테스트
- [x] `Standing_man.jpg` 테스트
- [x] `Bent_man.jpg` 테스트
- [x] 세 이미지 Positive Point 1개 테스트
- [x] 세 이미지 Positive Point 2개 테스트
- [x] 세 이미지 Positive Point 3개 테스트
- [x] Mask 결과 저장
- [x] Workflow JSON 저장
- [x] ComfyUI 실행 로그 확인
- [x] BentMan에서 BiRefNet과 동일 입력 조건 구성
- [ ] Peak VRAM 측정
- [ ] Ground Truth 기반 정량 평가
- [ ] 최종 사람 추출 방법 선정