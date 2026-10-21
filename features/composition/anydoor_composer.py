"""AnyDoor 상의 합성.

입력: 옷 사진(RGB) + 옷 윤곽(0/1) + 인물 사진(RGB) + 입힐 영역(0/1)
출력: 합성된 인물 사진 (RGB uint8, 인물 사진과 같은 크기)

- AnyDoor 폴더(기본 Desktop\\AnyDoor)의 run_inference.py는 고치지 않는다.
  scripts/anydoor_compose_test.py와 같은 방식으로 모델 로딩과 inference_single_image 부분만 읽어서 쓴다.
- 설정: 50스텝, float16 + save_memory (2026-10-11 확인: 화질 차이 없음)
- 모델 파일(16.8GB)은 본체 RAM에서 열고 모델 가중치(약 9.2GB)만 GPU로 옮긴다 (load_on_cpu).
  원래 코드는 파일 전체를 GPU에서 열어 10GB를 넘기고, 모자란 만큼 본체 메모리를 빌려 써서 느려졌다.
  (2026-10-13 측정: 같은 사진·seed로 1장 115초 → 60초, 결과 그림은 완전히 같음)
- 부품 단위 GPU 적재 (2026-10-21, _ONDEMAND_LOAD, _shift_out_first):
  - save_memory 동작: 부품을 두 묶음으로 나눠 사용 중인 묶음만 GPU에 적재.
    노이즈 제거 단계는 U-Net·ControlNet, 그 전후 단계는 VAE·DINOv2
  - 기존 문제 1: 모델 적재 시 model.cuda()로 네 부품 전체를 GPU에 일괄 적재
  - 기존 문제 2: 묶음 교체 시 새 묶음 적재 후 기존 묶음 해제. 교체 시점마다 네 부품 동시 상주
  - 결과: VRAM 10GB 용량 초과, 공유 GPU 메모리 2.7~3.2GB 사용으로 합성 지연
  - 변경: 큰 부품 네 개를 CPU에 둔 상태로 시작, 묶음 교체 시 기존 묶음 해제 후 새 묶음 적재. 가중치·연산 방식 동일
  - 측정: 같은 사진·seed, 서버와 같은 순서인 예열 → SAM2 추출 → 합성 2회.
    합성 41.1·36.9초 → 23.6·20.7초, 공유 GPU 메모리 최대 3,199MB → 224MB, 결과 이미지 픽셀 단위 동일
- 모델은 처음 호출할 때 한 번만 불러오고 이후 재사용한다 (체크포인트 16.8GB라 시간이 걸림).
- warmup(): 짧은 합성을 한 번 미리 돌려 GPU 첫 실행 준비를 끝내 둔다 (서버 켤 때 사용).
- 합성 설정 (화면 "합성 설정" 팝업, 2026-10-17, AnyDoor 웹 데모 run_gradio_demo.py와 같은 동작):
  - shape_control (Enable Shape Control): 다시 그릴 영역을 입힐 영역을 감싼 사각형 대신 칠한 모양 그대로.
    run_inference.py에는 없는 기능이라 웹 데모 process_pairs의 같은 줄을 불러올 때 끼워 넣는다 (_patch_shape_control)
  - refine (Reference Mask Refine): AnyDoor에 들어 있는 작은 보정 모델(iseg/coarse_mask_refine.pth, CPU)로
    옷 윤곽 가장자리를 다듬은 뒤 합성 (refine_ref_mask)
"""
import os
import sys
from pathlib import Path

import numpy as np

ANYDOOR_DIR = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor"))
DDIM_STEPS = 50  # 기본 스텝 수. compose(steps=...)로 바꿀 수 있다


# run_inference.py process_pairs에서 다시 그릴 영역(collage_mask)을 사각형으로 채우는 줄
_BOX_LINE = "    collage_mask[y1:y2,x1:x2,:] = 1.0"


def _patch_shape_control(src):
    """칠한 모양 그대로: _MOA_SHAPE_CONTROL이 참이면 사각형 대신 칠한 모양(tar_mask의 잘라낸 부분)을 다시 그릴 영역으로.
    웹 데모(run_gradio_demo.py) process_pairs의 enable_shape_control 분기와 같다. AnyDoor 파일은 그대로 두고 불러온 글자만 바꾼다"""
    if _BOX_LINE not in src:
        raise RuntimeError("run_inference.py에서 collage_mask 사각형 줄을 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
    shape = (
        "\n    if _MOA_SHAPE_CONTROL:"
        "\n        _cy1, _cy2, _cx1, _cx2 = tar_box_yyxx_crop"
        "\n        _m = tar_mask[_cy1:_cy2, _cx1:_cx2].astype(np.float32)"
        "\n        collage_mask = np.stack([_m, _m, _m], -1)"
    )
    return src.replace(_BOX_LINE, _BOX_LINE + shape, 1)


# run_inference.py에서 불러온 모델 전체를 GPU로 옮기는 줄
_CUDA_LINE = "model = model.cuda()\n"
# 대체 코드: 큰 부품 네 개는 CPU에 유지, 나머지 소형 값만 GPU로 이동. 모델 device가 GPU로 설정되어 샘플러는 GPU에서 실행.
# 큰 부품은 합성 시 save_memory의 low_vram_shift가 필요한 묶음만 적재
_ONDEMAND_LOAD = """_moa_big = {n: getattr(model, n) for n in ('model', 'control_model', 'first_stage_model', 'cond_stage_model')}
for _n in _moa_big:
    setattr(model, _n, torch.nn.Identity())
model = model.cuda()
for _n, _m in _moa_big.items():
    setattr(model, _n, _m)
"""


def _shift_out_first(self, is_diffusing):
    """AnyDoor cldm.py low_vram_shift와 같은 묶음 교체. 미사용 묶음의 CPU 이동을 먼저 수행한 뒤 사용 묶음을 GPU에 적재.
    원래 순서인 적재 후 해제는 교체 시점에 네 부품이 동시에 GPU에 상주해 VRAM 10GB 초과"""
    import torch

    if is_diffusing:
        self.first_stage_model = self.first_stage_model.cpu()
        self.cond_stage_model = self.cond_stage_model.cpu()
        torch.cuda.empty_cache()
        self.model = self.model.cuda()
        self.control_model = self.control_model.cuda()
    else:
        self.model = self.model.cpu()
        self.control_model = self.control_model.cpu()
        torch.cuda.empty_cache()
        self.first_stage_model = self.first_stage_model.cuda()
        self.cond_stage_model = self.cond_stage_model.cuda()


class AnyDoorComposer:
    def __init__(self, anydoor_dir=ANYDOOR_DIR, save_memory=True, fp16=True, load_on_cpu=True):
        self.anydoor_dir = Path(anydoor_dir).resolve()
        self.save_memory = save_memory
        self.fp16 = fp16
        self.load_on_cpu = load_on_cpu
        self._ns = None
        self._progress = None  # 합성 중에만 설정되는 진행률 알림 함수

    def _load(self):
        if self._ns is not None:
            return self._ns

        src = (self.anydoor_dir / "run_inference.py").read_text(encoding="utf-8")
        src = src.split("if __name__ == '__main__':")[0]
        src = _patch_shape_control(src)
        if self.save_memory:
            # AnyDoor 원래 옵션: 안 쓰는 부품을 CPU로 옮기고(low_vram_shift) attention을 나눠 계산
            src = src.replace("save_memory = False", "save_memory = True", 1)
        if self.load_on_cpu:
            # 모델 파일을 본체 RAM에서 열고, 다음 줄 model.cuda()가 합성에 쓰는 가중치만 GPU로 옮긴다
            if "location='cuda'" not in src:
                raise RuntimeError("run_inference.py에서 location='cuda'를 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
            src = src.replace("location='cuda'", "location='cpu'", 1)
        if self.save_memory and self.load_on_cpu:
            # 큰 부품 CPU 유지 상태로 시작. 부품 단위 GPU 적재, 맨 위 설명 참고
            if _CUDA_LINE not in src:
                raise RuntimeError("run_inference.py에서 model = model.cuda()를 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
            src = src.replace(_CUDA_LINE, _ONDEMAND_LOAD, 1)
        # 스텝 수: run_inference.py 안의 고정값 50을 호출마다 바꿀 수 있는 값으로 (AnyDoor 파일은 그대로)
        if "ddim_steps = 50" not in src:
            raise RuntimeError("run_inference.py에서 ddim_steps = 50을 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
        src = src.replace("ddim_steps = 50", "ddim_steps = _MOA_DDIM_STEPS", 1)

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

        if self.save_memory and self.load_on_cpu:
            # 묶음 교체 순서 변경: 해제 후 적재. AnyDoor 원본 파일 수정 없이 이 모델에만 적용
            import types
            ns["model"].low_vram_shift = types.MethodType(_shift_out_first, ns["model"])

        if self.fp16:
            # autocast에서는 복원 이미지가 float16으로 나오는데 AnyDoor의 crop_back(cv2.resize)이 처리하지 못한다.
            # AnyDoor 코드는 그대로 두고 복원 결과만 float32로 바꾼다 (scripts/anydoor_compose_test.py와 같음)
            model = ns["model"]
            decode = model.decode_first_stage
            model.decode_first_stage = lambda *a, **k: decode(*a, **k).float()

        # 진행률: DDIM 샘플러가 스텝마다 부르는 callback을 끼워 넣는다 (AnyDoor 코드 수정 없음)
        sampler = ns["ddim_sampler"]
        sample = sampler.sample

        def sample_with_progress(*args, **kwargs):
            if self._progress is not None:
                kwargs["callback"] = lambda i: self._progress((i + 1) / ns["_MOA_DDIM_STEPS"])
            return sample(*args, **kwargs)

        sampler.sample = sample_with_progress
        ns["_MOA_SHAPE_CONTROL"] = False
        self._ns = ns
        return ns

    def compose(self, ref_rgb, ref_mask, tar_rgb, tar_mask, seed=None, on_progress=None, steps=DDIM_STEPS,
                shape_control=False, refine=False):
        """합성 결과(RGB uint8)를 돌려준다.

        ref_rgb, tar_rgb : np.uint8 (H, W, 3) RGB
        ref_mask, tar_mask: np.uint8 (H, W) 0/1. AnyDoor는 tar_mask를 감싸는 사각형만 쓴다
        seed       : 같은 seed면 같은 결과 (None이면 무작위)
        on_progress: 0~1 진행률을 받는 함수 (스텝마다 호출)
        steps      : DDIM 스텝 수 (기본 50). 줄이면 빨라지지만 품질이 바뀔 수 있다
        shape_control: 참이면 칠한 모양 그대로 다시 그림 (거짓이면 칠한 영역을 감싼 사각형)
        refine     : 참이면 옷 윤곽 가장자리를 보정 모델로 다듬은 뒤 합성
        """
        import torch

        ns = self._load()
        ns["_MOA_DDIM_STEPS"] = int(steps)
        ns["_MOA_SHAPE_CONTROL"] = bool(shape_control)
        if refine:
            ref_mask = self.refine_ref_mask(ref_rgb, ref_mask)
        if seed is not None:
            ns["seed_everything"](int(seed))
        self._progress = on_progress
        try:
            with torch.autocast("cuda", dtype=torch.float16, enabled=self.fp16):
                gen = ns["inference_single_image"](ref_rgb, ref_mask, tar_rgb.copy(), tar_mask)
        finally:
            self._progress = None
        return np.clip(gen, 0, 255).astype(np.uint8)

    def refine_ref_mask(self, ref_rgb, ref_mask, max_side=1024):
        """옷 윤곽(0/1)을 AnyDoor의 보정 모델(iseg)로 다듬는다. 웹 데모 process_image_mask와 같음 (CPU, GPU 안 씀).
        큰 사진은 긴 변 max_side로 줄여 계산하고 원래 크기로 되돌린다. 보정 결과가 비면 원래 윤곽을 쓴다"""
        import cv2
        import torch

        if getattr(self, "_iseg", None) is None:
            if str(self.anydoor_dir) not in sys.path:
                sys.path.insert(0, str(self.anydoor_dir))
            from iseg.coarse_mask_refine_util import BaselineModel

            model = BaselineModel().eval()
            path = self.anydoor_dir / "iseg" / "coarse_mask_refine.pth"
            weights = torch.load(path, map_location="cpu", weights_only=True)["state_dict"]
            model.load_state_dict(weights, strict=True)
            self._iseg = model

        h, w = ref_mask.shape
        sc = min(1.0, max_side / max(h, w))
        img, mask = ref_rgb, ref_mask
        if sc < 1.0:
            size = (round(w * sc), round(h * sc))
            img = cv2.resize(ref_rgb, size, interpolation=cv2.INTER_AREA)
            mask = cv2.resize(ref_mask, size, interpolation=cv2.INTER_NEAREST)
        x = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1))).float().div(255).unsqueeze(0)
        m = torch.from_numpy(mask.astype(np.float32)).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            pred = (self._iseg(x, m)["instances"][0, 0].numpy() > 0.5).astype(np.uint8)
        if sc < 1.0:
            pred = cv2.resize(pred, (w, h), interpolation=cv2.INTER_NEAREST)
        return pred if pred.sum() > 0 else ref_mask

    def warmup(self, steps=2):
        """모델을 불러오고 짧은 합성을 한 번 돌린다. 결과는 버린다.
        GPU는 계산을 처음 할 때 계산 방식 고르기·메모리 잡기 준비를 한다(float16은 따로 필요).
        미리 해 두면 첫 사용자도 처음부터 빠른 속도로 받는다."""
        size = 256
        img = np.random.default_rng(0).integers(0, 256, (size, size, 3), dtype=np.uint8)
        mask = np.zeros((size, size), np.uint8)
        mask[64:192, 64:192] = 1
        self.compose(img, mask, img, mask, steps=steps)


_default = None


def _get_default():
    global _default
    if _default is None:
        _default = AnyDoorComposer()
    return _default


def compose(ref_rgb, ref_mask, tar_rgb, tar_mask, seed=None, on_progress=None, steps=DDIM_STEPS,
            shape_control=False, refine=False):
    """모듈 단위 진입점. 기본 composer를 한 번만 만들어 재사용한다."""
    return _get_default().compose(ref_rgb, ref_mask, tar_rgb, tar_mask, seed=seed, on_progress=on_progress, steps=steps,
                                  shape_control=shape_control, refine=refine)


def warmup(steps=2):
    """모듈 단위 예열. 기본 composer의 모델을 불러오고 짧은 합성을 한 번 돌린다."""
    _get_default().warmup(steps=steps)
