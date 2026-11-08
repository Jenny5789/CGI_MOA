"""AnyDoor 가중치 파일에서 합성에 쓰는 가중치(state_dict)만 남겨 새 파일로 저장한다.

학습을 이어서 할 때만 쓰는 값(optimizer_states 등)을 빼서, 파일 크기와
모델을 불러올 때의 메모리 최고치를 줄인다. 원본 파일은 바꾸지 않는다.
저장한 뒤 새 파일의 가중치가 원본과 모두 같은지 비교한다.

사용:
    python scripts/make_inference_ckpt.py 원본.ckpt 새파일.ckpt
"""
import sys
from pathlib import Path

import torch


def load(path):
    # mmap: 파일을 한꺼번에 메모리에 올리지 않고 필요한 부분만 읽음
    return torch.load(path, map_location="cpu", mmap=True, weights_only=False)


def main():
    if len(sys.argv) != 3:
        sys.exit("사용: python scripts/make_inference_ckpt.py 원본.ckpt 새파일.ckpt")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        sys.exit(f"이미 있는 파일이라 멈춤: {dst}")

    ckpt = load(src)
    print("원본 안의 항목:", ", ".join(ckpt.keys()))
    if "state_dict" not in ckpt:
        sys.exit("state_dict가 없어 멈춤: 이미 가중치만 든 파일일 수 있음")

    state = ckpt["state_dict"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": state}, dst)
    print(f"저장: {dst} ({dst.stat().st_size:,} 바이트, 가중치 {len(state):,}개)")

    new = load(dst)["state_dict"]
    same = new.keys() == state.keys() and all(torch.equal(new[k], state[k]) for k in state)
    print("비교: 원본과 모두 같음" if same else "비교: 다른 값이 있음 (새 파일을 쓰지 말 것)")


if __name__ == "__main__":
    main()