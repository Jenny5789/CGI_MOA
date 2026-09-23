# AnyDoor Baseline

## 1. 목적

MOA의 이미지 합성 방법을 비교하기 위한 첫 번째 Baseline.

공식 AnyDoor의 pretrained checkpoint와 기본 inference 설정을 사용하여
합성 결과와 실행 성능을 기록한다.

이후 다른 합성 방법과 동일한 입력 조건에서 비교한다.


## 2. 실행 환경

- GPU: NVIDIA GeForce RTX 3080
- 전용 VRAM: 10 GB


## 3. 모델

- Model: AnyDoor
- Checkpoint: epoch=1-step=8687.ckpt
- Pretrained model 사용
- 추가 학습/Fine-tuning 없음


## 4. 현재 추론 설정

- Working Resolution: 512 × 512
- DDIM Steps: 50
- Guidance Scale: 5.0
- Strength: 1
- Eta: 0.0
- Num Samples: 1


## 5. 테스트 입력

- Reference Image: examples/TestDreamBooth/FG/01.png
- Target Image: examples/TestDreamBooth/BG/000000309203_GT.png
- Target Mask: examples/TestDreamBooth/BG/000000309203_mask.png
- Reference Mask: Reference PNG의 Alpha Channel 사용


## 6. 실행 결과

- 실행 성공 여부: 성공
- DDIM Sampling Time: 15분 08초
- DDIM 평균 속도: 18.16 sec/step
- DDIM Steps: 50
- 전체 Inference Time: 미측정
- Peak VRAM: 미측정
- 실행 중 관찰: RTX 3080 전용 VRAM 약 9.7 / 10.0 GB 사용,
  Windows 작업 관리자에서 공유 GPU 메모리 사용 확인
- Output: experiments/anydoor_wrapper_test.png

### 실행 환경 참고

- xFormers CUDA Extension 비활성화
- Triton 미사용
- 일부 최적화가 적용되지 않은 상태에서 실행

## 7. 결과 관찰

- 객체 형태 보존:
- 객체 위치:
- 경계 자연스러움:
- 기타 문제:


## 8. 추후 비교

현재 AnyDoor 결과를 기준으로 이후 MOA 합성 방법과 비교한다.

비교 예정 항목:
- 객체 형태 보존
- 위치/크기 제어
- 경계 품질
- 처리 시간
- VRAM 사용량
- 최종 합성 자연스러움