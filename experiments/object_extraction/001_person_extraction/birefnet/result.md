# BiRefNet 사람 추출 테스트

- 실험일: 2026-09-21
- 실험 이미지: `Girl.jpg`
- 실험 단계: 사람 추출 / BiRefNet 테스트

## 1. 테스트 목적

MOA의 사람 이미지 추출 기능에 BiRefNet을 적용하고,
실제 사람 이미지에서 배경 제거 결과와 Mask가 정상적으로 생성되는지 확인한다.

---

## 2. 입력 이미지

- 파일명: `Girl.jpg`
- 이미지 크기: 975 × 1463

입력 이미지는 MOA 실험 폴더의 다음 위치에 저장하였다.

`experiments/object_extraction/001_person_extraction/inputs/Girl.jpg`

---

## 3. 사용 모델

- 모델: BiRefNet
- 모델 파일: `birefnet.safetensors`
- 모델 파일 크기: Windows 탐색기 표시 기준 약 434 MB
- 실행 도구: ComfyUI

ComfyUI에서 `Remove Background (BiRefNet)` 노드를 사용하였다.

모델 파일은 다음 위치에 배치하였다.

`ComfyUI/models/background_removal/birefnet.safetensors`

모델 파일을 배치한 뒤 ComfyUI를 재시작하였고,
이후 BiRefNet 노드가 정상적으로 실행되었다.

---

## 4. 실행 Workflow

실제 구성한 흐름은 다음과 같다.

`Load Image`
→ `Remove Background (BiRefNet)`

BiRefNet에서는 두 종류의 출력을 확인하였다.

### 배경 제거 결과

`IMAGE`
→ `Preview Image`
→ `Save Image`

### Mask

`mask`
→ `Mask to Image`
→ `Preview Image`
→ `Save Image`

---

## 5. 실행 결과

BiRefNet 실행에 성공하였다.

입력 이미지에서 사람이 분리된 IMAGE 결과가 생성되었고,
사람 영역을 나타내는 Mask도 함께 생성되었다.

저장한 결과 파일:

- `Girl_BiRefNet_extracted_00001_.png`
- `Girl_BiRefNet_mask_00001_.png`

저장 위치:

`experiments/object_extraction/001_person_extraction/birefnet/`

---

## 6. 실행 시간 기록

ComfyUI CMD 로그에서 다음 내용을 확인하였다.

첫 번째 실행:

`Requested to load BiRefNet`

`Model BiRefNet prepared for dynamic VRAM loading. 419MB Staged. 0 patches attached. Force pre-loaded 268 weights: 4216 KB.`

`Prompt executed in 2.11 seconds`

이후 실행:

`Prompt executed in 0.10 seconds`

`Prompt executed in 0.33 seconds`

### 기록 시 주의

위 시간은 ComfyUI에서 출력한 `Prompt executed` 기준이다.

첫 번째 2.11초 실행에서는 로그상 BiRefNet 모델 준비 과정이 함께 발생하였다.

따라서 현재 기록된 값을 순수 BiRefNet 추론 시간으로 확정하지 않는다.

후속 실행의 0.10초와 0.33초 역시 현재 단계에서는 별도의 평균 추론 시간으로 계산하지 않는다.

---

## 7. GPU / VRAM

사용 GPU:

- NVIDIA GeForce RTX 3080
- VRAM 10 GB

이번 테스트에서는 Peak VRAM을 별도로 측정하지 않았다.

- Peak VRAM: 미측정

---

## 8. 결과 확인

배경 제거 IMAGE를 육안으로 확인하였다.

확인된 내용:

- 사람 전체가 배경에서 분리되어 출력되었다.
- 머리, 몸통, 팔, 다리, 의류, 신발이 결과에 포함되었다.
- 머리카락 및 의류 끝부분과 같은 가느다란 영역도 일부 결과에 포함되어 있다.

Mask도 별도로 확인하였다.

- 배경은 검은색으로 표시되었다.
- 추출된 사람 영역은 흰색으로 표시되었다.
- 사람의 전체적인 실루엣이 Mask에 포함되어 있다.
- 머리카락 및 의류 끝부분과 같은 가느다란 영역도 일부 Mask에 포함되어 있다.

---

## 9. 현재 단계에서 판단하지 않은 내용

이번 테스트에서는 정답 Mask(Ground Truth)와 비교하지 않았다.

따라서 다음 항목은 아직 판단하지 않는다.

- IoU
- Dice
- 정량적인 추출 정확도
- SAM2 대비 성능 우열
- 평균 추론 시간
- Peak VRAM 비교

이번 테스트에서 확인한 것은
`Girl.jpg`를 입력했을 때 BiRefNet이 ComfyUI에서 정상 실행되고,
사람 추출 IMAGE와 Mask를 생성 및 저장할 수 있다는 것이다.

---

## 10. 현재 테스트 상태

- [x] BiRefNet 모델 준비
- [x] ComfyUI에서 모델 인식
- [x] `Girl.jpg` 입력
- [x] BiRefNet 실행
- [x] 배경 제거 IMAGE 확인
- [x] Mask 확인
- [x] 배경 제거 IMAGE 저장
- [x] Mask 저장
- [x] ComfyUI 실행 로그 확인
- [ ] Peak VRAM 측정
- [ ] 정량 평가
- [ ] 동일 이미지 SAM2 결과와 비교

---

# 추가 테스트 — Standingman

- 실험일: 2026-09-22
- 실험 이미지: `Standingman.jpg`
- 실험 단계: 사람 추출 / BiRefNet 추가 테스트

## 11. 입력 이미지

- 파일명: `Standingman.jpg`
- 이미지 크기: 3000 × 5332

입력 위치:

`experiments/object_extraction/001_person_extraction/inputs/Standingman.jpg`

---

## 12. 실행 조건

기존 `Girl.jpg` 테스트와 동일한 BiRefNet Workflow를 사용하였다.

실행 흐름:

`Load Image`

→ `Remove Background (BiRefNet)`

출력:

- 배경 제거 IMAGE
- Mask

별도의 Point Prompt는 사용하지 않았다.

---

## 13. 실행 결과

BiRefNet 실행에 성공하였다.

저장 결과:

- `Standingman_BiRefNet_extracted_00001_.png`
- `Standingman_BiRefNet_mask_00001_.png`

Workflow:

- `Standingman_BiRefNet_workflow.json`

저장 위치:

`experiments/object_extraction/001_person_extraction/birefnet/`

---

## 14. 실행 시간 기록

ComfyUI CMD 로그:

`Requested to load BiRefNet`

`Model BiRefNet prepared for dynamic VRAM loading. 419MB Staged. 0 patches attached. Force pre-loaded 268 weights: 4216 KB.`

`Prompt executed in 7.00 seconds`

### 기록 시 주의

로그상 이번 실행에서는 BiRefNet 모델 준비 과정이 함께 발생하였다.

따라서 `7.00 seconds`를 순수 BiRefNet 추론 시간으로 사용하지 않는다.

현재 단계에서는 ComfyUI 실행 로그 원본 값으로만 기록한다.

---

## 15. 결과 확인

배경 제거 IMAGE와 Mask를 육안으로 확인하였다.

확인된 내용:

- 머리부터 신발까지 사람 전체가 결과에 포함되었다.
- 사람 영역이 하나의 연속된 Mask로 생성되었다.
- 두 다리 사이의 배경이 분리되어 있다.
- `Girl.jpg` 결과에서 관찰되었던 큰 내부 누락은 현재 결과에서 보이지 않았다.
- 현재 육안 확인 범위에서는 사람과 떨어진 큰 배경 영역이 Mask에 포함된 모습은 보이지 않았다.

Ground Truth Mask가 없으므로 실제 경계 정확도는 판단하지 않는다.

---

## 16. 현재 상태

- [x] `Standingman.jpg` 입력
- [x] BiRefNet 실행
- [x] 배경 제거 IMAGE 확인
- [x] Mask 확인
- [x] 결과 파일 저장
- [x] MOA 실험 폴더에 결과 복사
- [x] Workflow JSON 저장
- [x] 실행 로그 확인
- [ ] Peak VRAM 측정
- [ ] Ground Truth 기반 정량 평가
---

# 추가 테스트 — BentMan

- 실험일: 2026-09-23
- 원본 이미지: `Bent_man.jpg`
- 실험 입력 이미지: `Bent_man_2791x4096.jpg`
- 실험 단계: 사람 추출 / BiRefNet 추가 테스트
- 비교 목적: SAM2와 동일한 입력 이미지를 사용한 사람 추출 비교

## 17. 입력 이미지

원본 이미지:

- 파일명: `Bent_man.jpg`
- 이미지 크기: 3536 × 5304

원본 위치:

`experiments/object_extraction/001_person_extraction/inputs/Bent_man.jpg`

SAM2 Points Editor의 최대 height 4096 제한을 고려하여
원본의 가로세로 비율을 유지한 공통 실험 이미지를 별도로 생성하였다.

공통 실험 이미지:

- 파일명: `Bent_man_2791x4096.jpg`
- 이미지 크기: 2791 × 4096

저장 위치:

`experiments/object_extraction/001_person_extraction/inputs/Bent_man_2791x4096.jpg`

이번 테스트에서는 BiRefNet과 SAM2 모두
동일한 `Bent_man_2791x4096.jpg`를 입력으로 사용하였다.

---

## 18. 실행 조건

기존 테스트와 동일한 BiRefNet Workflow를 사용하였다.

실행 흐름:

`Load Image`

→ `Remove Background (BiRefNet)`

출력:

- 배경 제거 IMAGE
- Mask

별도의 Point Prompt는 사용하지 않았다.

Workflow:

`Bent_man_BiRefNet_workflow.json`

---

## 19. 실행 결과

BiRefNet 실행에 성공하였다.

배경이 제거된 사람 IMAGE와 Mask가 생성되었다.

저장 결과:

- `Bent_man_BiRefNet_extracted_00001_.png`
- `Bent_man_BiRefNet_mask_00001_.png`

Workflow:

- `Bent_man_BiRefNet_workflow.json`

저장 위치:

`experiments/object_extraction/001_person_extraction/birefnet/`

---

## 20. 실행 시간 기록

ComfyUI CMD 로그:

`Requested to load BiRefNet`

`Model BiRefNet prepared for dynamic VRAM loading. 419MB Staged. 0 patches attached. Force pre-loaded 268 weights: 4216 KB.`

`Prompt executed in 5.78 seconds`

### 기록 시 주의

로그상 BiRefNet 모델 준비 과정이 함께 발생하였다.

따라서 `5.78 seconds`를 순수 BiRefNet 추론 시간으로 사용하지 않는다.

현재 단계에서는 ComfyUI Workflow 실행 당시의 로그 원본 값으로만 기록한다.

Peak VRAM은 별도로 측정하지 않았다.

- Peak VRAM: 미측정

---

## 21. 결과 확인

배경 제거 IMAGE와 Mask를 육안으로 확인하였다.

확인된 내용:

- 크게 허리를 숙인 자세에서도 머리부터 신발까지 사람 전체가 결과에 포함되었다.
- 머리, 몸통, 뒤로 뻗은 팔, 하체와 신발이 하나의 사람 영역으로 연결되어 있다.
- Mask 내부에서 눈에 띄는 큰 누락 영역은 관찰되지 않았다.
- 머리카락의 전체적인 외곽 형태가 Mask에 포함되었다.
- 배경 제거 IMAGE에서는 일부 가느다란 머리카락 영역도 확인되었다.
- 현재 육안 확인 범위에서는 사람과 떨어진 큰 배경 영역이 Mask에 포함된 모습은 보이지 않았다.
- 손목시계, 목걸이, 바지 체인과 같이 사람에게 착용된 작은 요소가 일부 추출 결과에 포함되어 있다.

Ground Truth Mask가 없으므로
머리카락, 손가락, 액세서리 등의 실제 경계 정확도는 판단하지 않는다.

---

## 22. 현재 상태

- [x] 원본 `Bent_man.jpg` 보존
- [x] 공통 입력 `Bent_man_2791x4096.jpg` 생성
- [x] BiRefNet과 SAM2의 동일 입력 조건 구성
- [x] BiRefNet 실행
- [x] 배경 제거 IMAGE 확인
- [x] Mask 확인
- [x] 결과 파일 저장
- [x] MOA 실험 폴더에 결과 복사
- [x] Workflow JSON 저장
- [x] 실행 로그 확인
- [ ] Peak VRAM 측정
- [ ] Ground Truth 기반 정량 평가