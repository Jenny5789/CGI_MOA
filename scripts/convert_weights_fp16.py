"""AnyDoor 합성 가중치를 16비트 추론용 파일로 변환한다.

- 남기는 값: 합성에 쓰는 가중치 state_dict만. optimizer_states 같은 학습 전용 값은 제외
- 16비트 변환: U-Net·ControlNet·VAE·DINOv2 네 부품. 확산 일정 값 13개는 32비트 유지
- 크기: 재학습 가중치 9.8GB, 공식 가중치 16.8GB 모두 약 4.9GB로 감소
- 합성 서버 사용: 환경 변수 ANYDOOR_CKPT에 새 파일 경로 지정
- 원본 파일은 바꾸지 않고, 저장 후 새 파일 값이 변환 값과 모두 같은지 확인

사용:
    python scripts/convert_weights_fp16.py 원본.ckpt 새파일.ckpt
"""
import sys
from pathlib import Path

import torch

# 16비트로 바꾸는 부품. features/composition/anydoor_composer.py의 _BIG_PARTS와 같음
PARTS = ("model.", "control_model.", "first_stage_model.", "cond_stage_model.")
# 합성 서버는 DINOv2 사전 학습 파일을 읽지 않으므로 합성 가중치 파일 안에 DINOv2 값이 있어야 함
DINOV2 = "cond_stage_model.model."


def load(path):
    # mmap: 파일 전체를 RAM에 복사하지 않고 필요한 부분만 읽음
    return torch.load(path, map_location="cpu", mmap=True, weights_only=False)


def main():
    if len(sys.argv) != 3:
        sys.exit("사용: python scripts/convert_weights_fp16.py 원본.ckpt 새파일.ckpt")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        sys.exit(f"이미 있는 파일이라 멈춤: {dst}")

    ckpt = load(src)
    state = ckpt.get("state_dict", ckpt)
    if not any(k.startswith(DINOV2) for k in state):
        sys.exit("DINOv2 값이 없어 멈춤: 합성 서버에서 쓸 수 없는 파일")

    half = {k: v.half() if k.startswith(PARTS) and v.is_floating_point() else v for k, v in state.items()}
    n16 = sum(v.dtype == torch.float16 for v in half.values())
    dst.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": half}, dst)
    print(f"저장: {dst}, {dst.stat().st_size:,}바이트, 가중치 {len(half):,}개 중 16비트 {n16:,}개")

    new = load(dst)["state_dict"]
    same = new.keys() == half.keys() and all(torch.equal(new[k], half[k]) for k in half)
    print("확인: 변환 값과 모두 같음" if same else "확인: 다른 값이 있음, 새 파일 사용 금지")


if __name__ == "__main__":
    main()
