"""AnyDoor 상의 합성.

입력: 옷 사진(RGB) + 옷 윤곽(0/1) + 인물 사진(RGB) + 입힐 영역(0/1)
출력: 합성된 인물 사진 (RGB uint8, 인물 사진과 같은 크기)

- AnyDoor 폴더(기본 Desktop\\AnyDoor)의 run_inference.py는 고치지 않는다.
  모델 로딩과 inference_single_image 부분만 읽어서 쓴다.
- 설정: 50스텝, float16 + save_memory (2026-10-11 확인: 1장 약 4분, 화질 차이 없음)
- 모델은 처음 호출할 때 한 번만 불러오고 이후 재사용한다 (체크포인트 16.8GB라 시간이 걸림).
"""
import os
import sys
from pathlib import Path

import numpy as np

ANYDOOR_DIR = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor"))
DDIM_STEPS = 50  # run_inference.py의 ddim_steps와 같아야 진행률이 맞는다


class AnyDoorComposer:
    def __init__(self, anydoor_dir=ANYDOOR_DIR, save_memory=True, fp16=True):
        self.anydoor_dir = Path(anydoor_dir).resolve()
        self.save_memory = save_memory
        self.fp16 = fp16
        self._ns = None
        self._progress = None  # 합성 중에만 설정되는 진행률 알림 함수

    def _load(self):
        if self._ns is not None:
            return self._ns

        src = (self.anydoor_dir / "run_inference.py").read_text(encoding="utf-8")
        src = src.split("if __name__ == '__main__':")[0]
        if self.save_memory:
            # AnyDoor 원래 옵션: 안 쓰는 부품을 CPU로 옮기고(low_vram_shift) attention을 나눠 계산
            src = src.replace("save_memory = False", "save_memory = True", 1)

        # run_inference.py가 ./configs/... 같은 상대 경로를 쓰므로 불러오는 동안만 AnyDoor 폴더로 이동
        if str(self.anydoor_dir) not in sys.path:
            sys.path.insert(0, str(self.anydoor_dir))
        prev_cwd = os.getcwd()
        os.chdir(self.anydoor_dir)
        try:
            ns = {"__name__": "anydoor_inference"}
            exec(compile(src, str(self.anydoor_dir / "run_inference.py"), "exec"), ns)
        finally:
            os.chdir(prev_cwd)

        if self.fp16:
            # autocast에서는 복원 이미지가 float16으로 나오는데 AnyDoor의 crop_back(cv2.resize)이 처리하지 못한다.
            # AnyDoor 코드는 그대로 두고 복원 결과만 float32로 바꾼다
            model = ns["model"]
            decode = model.decode_first_stage
            model.decode_first_stage = lambda *a, **k: decode(*a, **k).float()

        # 진행률: DDIM 샘플러가 스텝마다 부르는 callback을 끼워 넣는다 (AnyDoor 코드 수정 없음)
        sampler = ns["ddim_sampler"]
        sample = sampler.sample

        def sample_with_progress(*args, **kwargs):
            if self._progress is not None:
                kwargs["callback"] = lambda i: self._progress((i + 1) / DDIM_STEPS)
            return sample(*args, **kwargs)

        sampler.sample = sample_with_progress
        self._ns = ns
        return ns

    def compose(self, ref_rgb, ref_mask, tar_rgb, tar_mask, seed=None, on_progress=None):
        """합성 결과(RGB uint8)를 돌려준다.

        ref_rgb, tar_rgb : np.uint8 (H, W, 3) RGB
        ref_mask, tar_mask: np.uint8 (H, W) 0/1. AnyDoor는 tar_mask를 감싸는 사각형만 쓴다
        seed       : 같은 seed면 같은 결과 (None이면 무작위)
        on_progress: 0~1 진행률을 받는 함수 (스텝마다 호출)
        """
        import torch

        ns = self._load()
        if seed is not None:
            ns["seed_everything"](int(seed))
        self._progress = on_progress
        try:
            with torch.autocast("cuda", dtype=torch.float16, enabled=self.fp16):
                gen = ns["inference_single_image"](ref_rgb, ref_mask, tar_rgb.copy(), tar_mask)
        finally:
            self._progress = None
        return np.clip(gen, 0, 255).astype(np.uint8)


_default = None


def compose(ref_rgb, ref_mask, tar_rgb, tar_mask, seed=None, on_progress=None):
    """모듈 단위 진입점. 기본 composer를 한 번만 만들어 재사용한다."""
    global _default
    if _default is None:
        _default = AnyDoorComposer()
    return _default.compose(ref_rgb, ref_mask, tar_rgb, tar_mask, seed=seed, on_progress=on_progress)
