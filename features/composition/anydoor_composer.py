"""AnyDoor 상의 합성.

입력: 옷 사진(RGB) + 옷 윤곽(0/1) + 인물 사진(RGB) + 입힐 영역(0/1)
출력: 합성된 인물 사진 (RGB uint8, 인물 사진과 같은 크기)

- AnyDoor 폴더(기본 Desktop\\AnyDoor)의 run_inference.py는 고치지 않는다.
  모델 로딩과 inference_single_image 부분만 읽어서 쓴다 (docs/작업일지.md 2026-10-12 ⑤).
- 설정: 50스텝, 16비트 연산·가중치
- 인물 사진에서 잘라 다시 그리는 정사각형: AnyDoor 기본 1.5~2.9배 무작위 → 1.3배 고정
  (2026-10-12 결정: 배율 비교 실험에서 머리카락·귀걸이 유지가 낫고 옷 변형이 가장 적음, run_inference.py는 그대로)
- 가중치 적재 2026-11-09, _load_weights:
  - mmap 적재: 가중치 파일을 RAM에 통째로 복사하지 않고 필요한 부분만 읽음. 원본 파일의 학습 전용 값 7.0GB는 읽지 않음
  - 16비트 가중치: U-Net·ControlNet·VAE·DINOv2 네 부품을 16비트로 바꿔 9.8GB를 4.9GB로 줄임. 확산 일정 값은 32비트 유지
  - DINOv2 중복 적재 생략: 사전 학습 파일 4.5GB와 같은 값 567개가 합성 가중치 파일에 모두 있어 빈 값으로 만든 뒤 덮어씀
  - 네 부품 GPU 상주: 16비트 기준 SAM2와 함께 올려도 VRAM 10GB 이내라 부품 교체 없이 모두 GPU에 둠
  - ANYDOOR_CKPT: 16비트 추론용 파일 경로. scripts/convert_weights_fp16.py로 생성. 비우면 configs/inference.yaml의 원본 파일
  - 측정: 서버와 같은 순서인 SAM2 적재·추출 → 예열 → 합성 3쌍, 32비트 부품 교체 방식 대비
    합성 22.4~29.3초 → 15.3~17.0초, RAM 최고 22.2GB → 13.7GB, GPU 전용 최고 8.81GB → 7.08GB,
    공유 GPU 메모리 최고 212MB → 84MB, 결과 평균 픽셀 차이 0.047~0.109/255
- save_memory=True: VRAM이 더 작은 GPU용 부품 단위 적재 2026-10-21, _ONDEMAND_LOAD, _shift_out_first
  - 부품을 두 묶음으로 나눠 사용 중인 묶음만 GPU에 적재. 노이즈 제거 단계는 U-Net·ControlNet, 그 전후 단계는 VAE·DINOv2
  - 묶음 교체 순서: 기존 묶음 해제 후 새 묶음 적재. AnyDoor 원래 순서는 교체 시점에 네 부품이 동시에 GPU에 상주
  - 16비트 기준 GPU 전용 최고 4.35GB, 합성 15.7초
- 모델은 처음 호출할 때 한 번만 불러오고 이후 재사용한다.
- warmup(): 짧은 합성을 한 번 미리 돌려 GPU 첫 실행 준비를 끝내 둔다 (서버 켤 때 사용).
- 합성 설정 (화면 "합성 설정" 팝업, 2026-10-17, AnyDoor 웹 데모 run_gradio_demo.py와 같은 동작):
  - shape_control (Enable Shape Control): 다시 그릴 영역을 입힐 영역을 감싼 사각형 대신 칠한 모양 그대로.
    run_inference.py에는 없는 기능이라 웹 데모 process_pairs의 같은 줄을 불러올 때 끼워 넣는다 (_patch_shape_control)
  - refine (Reference Mask Refine): AnyDoor에 들어 있는 작은 보정 모델(iseg/coarse_mask_refine.pth, CPU)로
    옷 윤곽 가장자리를 다듬은 뒤 합성 (refine_ref_mask)
- 크롭 영역 기록 (2026-10-21): 합성마다 AnyDoor가 다시 그린 정사각형 위치를 last_crop_box에 보관 → 박스 선 보정(seam.py)에 사용
- 초해상도 복원 2026-11-10: 512 결과를 정사각형 크기로 키우기 전에 Real-ESRGAN x2로 1024 복원 후 축소, upscale.py.
  UPSCALE_CKPT 가중치 파일이 없으면 기존 방식
"""
import os
import sys
from pathlib import Path

import numpy as np

ANYDOOR_DIR = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor"))
ANYDOOR_CKPT = os.environ.get("ANYDOOR_CKPT") or None  # 합성 가중치 파일. 비우면 configs/inference.yaml의 pretrained_model
# 입력 형식 2026-11-10, retrain_input.py: anydoor = 원래 AnyDoor 입력, retrain = 팀 재학습 학습 재료와 같은 입력.
# 11/10 비교: 재학습 가중치도 앱 합성 영역 모양에서는 anydoor가 안정적이라 배포 기본은 anydoor, retrain은 시험용
INPUT_MODE = os.environ.get("ANYDOOR_INPUT", "anydoor")
# 초해상도 가중치 파일 2026-11-10, upscale.py. 빈 값이면 초해상도 끔, 파일이 없어도 끔
UPSCALE_CKPT = os.environ.get(
    "UPSCALE_CKPT", str(Path(__file__).resolve().parents[2] / "checkpoints" / "realesrgan" / "RealESRGAN_x2plus.pth"))
DDIM_STEPS = 50  # 기본 스텝 수. compose(steps=...)로 바꿀 수 있다
CROP_RATIO = 1.3  # 잘라 다시 그리는 정사각형 배율 (None이면 AnyDoor 기본 1.5~2.9배 무작위)


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


# 합성에 쓰는 큰 부품 네 개: U-Net, ControlNet, VAE, DINOv2. 가중치 2,451.9M개 중 99.9%
_BIG_PARTS = ("model", "control_model", "first_stage_model", "cond_stage_model")

# run_inference.py에서 모델을 만드는 줄과 가중치 파일 전체를 GPU에서 여는 줄
_CREATE_LINE = "model = create_model(model_config ).cpu()\n"
_LOAD_LINE = "model.load_state_dict(load_state_dict(model_ckpt, location='cuda'))\n"
# 대체 코드: DINOv2 인코더가 사전 학습 파일 대신 빈 값을 읽게 한 뒤 모델 생성, 가중치는 _load_weights로 적재
_CREATE_PATCH = """import ldm.modules.encoders.modules as _moa_enc
_moa_enc.DINOv2_weight_path = _moa_empty_state()
model = create_model(model_config ).cpu()
"""
_LOAD_PATCH = "_moa_load_weights(model, model_ckpt)\n"


def _empty_state():
    """DINOv2 중복 적재 생략용 빈 가중치. AnyDoor DINOv2 인코더는 생성 시 사전 학습 파일 4.5GB를 읽지만
    같은 값이 합성 가중치 파일에 모두 들어 있어 곧바로 덮어써진다. 2026-11-09 확인: 결과 픽셀 동일, 적재 약 20초 단축"""
    import io

    import torch

    buf = io.BytesIO()
    torch.save({}, buf)
    buf.seek(0)
    return buf


def _load_weights(model, path, half):
    """합성 가중치 적재. mmap으로 열어 파일 전체를 RAM에 복사하지 않고, 학습 전용 값은 읽지 않는다.
    half면 큰 부품 네 개를 16비트로 바꾼 뒤 적재. 32비트 파일도 적재 중에 16비트로 바뀐다"""
    import torch

    if half:
        for name in _BIG_PARTS:
            getattr(model, name).half()
    if str(path).lower().endswith(".safetensors"):
        import safetensors.torch

        state = safetensors.torch.load_file(str(path), device="cpu")
    else:
        state = torch.load(path, map_location="cpu", mmap=True, weights_only=False)
        state = state.get("state_dict", state)
    print(f"[MOA] AnyDoor 가중치 적재: {path}", flush=True)
    model.load_state_dict(state)


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
    def __init__(self, anydoor_dir=ANYDOOR_DIR, save_memory=False, fp16=True, ckpt=ANYDOOR_CKPT, crop_ratio=CROP_RATIO,
                 upscale_ckpt=UPSCALE_CKPT, input_mode=INPUT_MODE):
        """save_memory: 참이면 부품 단위 GPU 적재. fp16: 참이면 16비트 연산·가중치.
        ckpt: 합성 가중치 파일, 비우면 configs/inference.yaml의 pretrained_model
        upscale_ckpt: 초해상도 가중치 파일, 비우거나 파일이 없으면 기존처럼 512 결과를 그대로 확대"""
        self.anydoor_dir = Path(anydoor_dir).resolve()
        self.save_memory = save_memory
        self.fp16 = fp16
        self.ckpt = str(Path(ckpt).resolve()) if ckpt else None
        self.crop_ratio = crop_ratio
        self.upscale_ckpt = str(upscale_ckpt) if upscale_ckpt and Path(upscale_ckpt).is_file() else None
        self._upscaler = None
        self._ns = None
        self._progress = None  # 합성 중에만 설정되는 진행률 알림 함수
        self.last_crop_box = None  # 가장 최근 합성의 크롭 영역 (위, 아래, 왼쪽, 오른쪽), 박스 선 보정용
        self.last_upscaled = False  # 가장 최근 합성에 초해상도를 적용했는지
        self.input_mode = input_mode  # anydoor 또는 retrain
        self._keypoints = None  # retrain 입력에 쓸 관절 점, 합성 중에만 설정
        self.last_input = None  # 가장 최근 합성에 실제로 쓴 입력 형식

    def _load(self):
        if self._ns is not None:
            return self._ns

        src = (self.anydoor_dir / "run_inference.py").read_text(encoding="utf-8")
        src = src.split("if __name__ == '__main__':")[0]
        src = _patch_shape_control(src)
        if self.save_memory:
            # AnyDoor 원래 옵션: 안 쓰는 부품을 CPU로 옮기고(low_vram_shift) attention을 나눠 계산
            src = src.replace("save_memory = False", "save_memory = True", 1)
        # 모델 생성·가중치 적재: DINOv2 중복 적재 생략, mmap 적재, 16비트 변환. 맨 위 설명 참고
        for line in (_CREATE_LINE, _LOAD_LINE):
            if line not in src:
                raise RuntimeError(f"run_inference.py에서 {line.strip()}를 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
        src = src.replace(_CREATE_LINE, _CREATE_PATCH, 1).replace(_LOAD_LINE, _LOAD_PATCH, 1)
        if self.save_memory:
            # 큰 부품 CPU 유지 상태로 시작. 부품 단위 GPU 적재, 맨 위 설명 참고
            if _CUDA_LINE not in src:
                raise RuntimeError("run_inference.py에서 model = model.cuda()를 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
            src = src.replace(_CUDA_LINE, _ONDEMAND_LOAD, 1)
        # 스텝 수: run_inference.py 안의 고정값 50을 호출마다 바꿀 수 있는 값으로 (AnyDoor 파일은 그대로)
        if "ddim_steps = 50" not in src:
            raise RuntimeError("run_inference.py에서 ddim_steps = 50을 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
        src = src.replace("ddim_steps = 50", "ddim_steps = _MOA_DDIM_STEPS", 1)
        if self.crop_ratio is not None:
            # 정사각형 배율: expand_bbox가 randint(앞×10, 뒤×10)/10으로 뽑으므로 [1.3, 1.4]면 항상 1.3
            # (크롭 배율 비교 실험과 같은 값, docs/작업일지.md 2026-10-17 ②. 뽑기 횟수는 그대로라 같은 seed면 배율만 다른 결과)
            if "ratio=[1.5, 3]" not in src:
                raise RuntimeError("run_inference.py에서 ratio=[1.5, 3]을 찾지 못했습니다. AnyDoor 코드가 바뀌었는지 확인하세요.")
            r = round(float(self.crop_ratio), 1)
            src = src.replace("ratio=[1.5, 3]", f"ratio=[{r}, {round(r + 0.1, 1)}]", 1)

        # run_inference.py가 ./configs/... 같은 상대 경로를 쓰므로 불러오는 동안만 AnyDoor 폴더로 이동
        if str(self.anydoor_dir) not in sys.path:
            sys.path.insert(0, str(self.anydoor_dir))
        prev_cwd = os.getcwd()
        os.chdir(self.anydoor_dir)
        try:
            ns = {
                "__name__": "anydoor_inference",
                "_moa_empty_state": _empty_state,
                "_moa_load_weights": lambda model, path: _load_weights(model, self.ckpt or path, self.fp16),
            }
            exec(compile(src, str(self.anydoor_dir / "run_inference.py"), "exec"), ns)
        finally:
            os.chdir(prev_cwd)

        if self.save_memory:
            # 묶음 교체 순서 변경: 해제 후 적재. AnyDoor 원본 파일 수정 없이 이 모델에만 적용
            import types
            ns["model"].low_vram_shift = types.MethodType(_shift_out_first, ns["model"])

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
                kwargs["callback"] = lambda i: self._progress((i + 1) / ns["_MOA_DDIM_STEPS"])
            return sample(*args, **kwargs)

        sampler.sample = sample_with_progress

        # 크롭 영역 기록 (박스 선 보정용): process_pairs가 돌려주는 다시 그린 정사각형 위치를 보관 (AnyDoor 코드 수정 없음)
        process_pairs = ns["process_pairs"]

        def process_pairs_record(*args, **kwargs):
            # 재학습 입력: 관절 점이 있으면 팀 재학습 학습 재료와 같은 입력으로 구성, retrain_input.py
            if self._keypoints is not None:
                from .retrain_input import inference_item

                item = inference_item(*args, self._keypoints, ns)
                self.last_input = "retrain"
            else:
                item = process_pairs(*args, **kwargs)
                self.last_input = "anydoor"
            self.last_crop_box = tuple(int(v) for v in item["tar_box_yyxx_crop"])  # (위, 아래, 왼쪽, 오른쪽)
            return item

        ns["process_pairs"] = process_pairs_record

        # 초해상도 복원 2026-11-10: crop_back이 512 결과를 다시 그린 정사각형 크기로 키우기 전에 2배로 복원한 뒤 줄여서 넘긴다.
        # 정사각형이 512보다 클 때만 적용, AnyDoor 코드 수정 없음. upscale.py 설명 참고
        if self.upscale_ckpt:
            import cv2

            from .upscale import Upscaler

            self._upscaler = Upscaler(self.upscale_ckpt, device="cuda", half=self.fp16)
            print(f"[MOA] 초해상도 가중치 적재: {self.upscale_ckpt}", flush=True)
            crop_back = ns["crop_back"]

            def crop_back_upscaled(pred, tar_image, extra_sizes, tar_box_yyxx_crop):
                h2, w2 = int(extra_sizes[2]), int(extra_sizes[3])
                self.last_upscaled = max(h2, w2) > max(pred.shape[:2])
                if self.last_upscaled:
                    img = np.clip(pred, 0, 255).astype(np.uint8)
                    # AnyDoor가 첫 줄을 빼 511줄이 되므로 짝수로 맞춘 뒤 복원하고 다시 자름: pixel unshuffle 조건
                    pad = (img.shape[0] % 2, img.shape[1] % 2)
                    if any(pad):
                        img = np.pad(img, ((0, pad[0]), (0, pad[1]), (0, 0)), mode="edge")
                    up = self._upscaler(img)[: 2 * pred.shape[0], : 2 * pred.shape[1]]
                    pred = cv2.resize(up, (w2, h2), interpolation=cv2.INTER_AREA).astype(np.float32)
                return crop_back(pred, tar_image, extra_sizes, tar_box_yyxx_crop)

            ns["crop_back"] = crop_back_upscaled
        ns["_MOA_SHAPE_CONTROL"] = False
        self._ns = ns
        return ns

    def compose(self, ref_rgb, ref_mask, tar_rgb, tar_mask, seed=None, on_progress=None, steps=DDIM_STEPS,
                shape_control=False, refine=False, keypoints=None):
        """합성 결과(RGB uint8)를 돌려준다.

        ref_rgb, tar_rgb : np.uint8 (H, W, 3) RGB
        ref_mask, tar_mask: np.uint8 (H, W) 0/1. AnyDoor는 tar_mask를 감싸는 사각형만 쓴다
        seed       : 같은 seed면 같은 결과 (None이면 무작위)
        on_progress: 0~1 진행률을 받는 함수 (스텝마다 호출)
        steps      : DDIM 스텝 수 (기본 50). 줄이면 빨라지지만 품질이 바뀔 수 있다
        shape_control: 참이면 칠한 모양 그대로 다시 그림 (거짓이면 칠한 영역을 감싼 사각형)
        refine     : 참이면 옷 윤곽 가장자리를 보정 모델로 다듬은 뒤 합성
        keypoints  : input_mode가 retrain일 때 쓰는 인물 사진 관절 점, retrain_input.estimate_keypoints 결과.
                     비우면 원래 AnyDoor 입력
        """
        import torch

        ns = self._load()
        self._keypoints = keypoints if self.input_mode == "retrain" else None
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
            self._keypoints = None
        return np.clip(gen, 0, 255).astype(np.uint8)

    def refine_ref_mask(self, ref_rgb, ref_mask, max_side=1024):
        """옷 윤곽(0/1)을 AnyDoor의 보정 모델(iseg)로 다듬는다. 웹 데모 process_image_mask와 같음 (CPU, GPU 안 씀).
        큰 사진은 긴 변 max_side로 줄여 계산하고 원래 크기로 되돌린다. 보정 결과가 비면 원래 윤곽을 쓴다"""
        import cv2
        import torch

        # 보정 모델은 refine을 처음 쓸 때 한 번만 불러와 self._iseg에 보관한다. __init__에서 만들지 않으므로 getattr로 확인
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
        if self._upscaler is not None:  # 예열 합성은 정사각형이 작아 초해상도를 거치지 않으므로 따로 한 번 실행
            self._upscaler(img[:64, :64])


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


def last_crop_box():
    """기본 composer의 가장 최근 합성 크롭 영역 (위, 아래, 왼쪽, 오른쪽). 합성 전이면 None"""
    return _get_default().last_crop_box
