from pathlib import Path
import sys
import os

import cv2
import einops
import numpy as np
import torch

from omegaconf import OmegaConf

# 프로젝트 경로
MOA_ROOT = Path(__file__).resolve().parent.parent
ANYDOOR_ROOT = Path.home() / "Desktop" / "AnyDoor"

# MOA에서 AnyDoor 내부 코드를 사용할 수 있도록 경로 추가
sys.path.insert(0, str(ANYDOOR_ROOT))
sys.path.insert(0, str(ANYDOOR_ROOT / "dinov2"))

from cldm.model import create_model, load_state_dict
from cldm.ddim_hacked import DDIMSampler
from datasets.data_utils import *


# AnyDoor 모델과 checkpoint 준비
def load_anydoor_model():
    """기존 AnyDoor 모델과 checkpoint를 불러온다."""

    original_dir = Path.cwd()

    try:
        os.chdir(ANYDOOR_ROOT)

        config_path = ANYDOOR_ROOT / "configs" / "inference.yaml"
        config = OmegaConf.load(config_path)

        model_config = ANYDOOR_ROOT / config.config_file
        model_ckpt = Path(config.pretrained_model)

        model = create_model(str(model_config)).cpu()

        model.load_state_dict(
            load_state_dict(str(model_ckpt), location="cuda")
        )

        model = model.cuda()

        ddim_sampler = DDIMSampler(model)

        return model, ddim_sampler

    finally:
        os.chdir(original_dir)


# Reference와 Target을 AnyDoor 입력 형태로 전처리
def process_anydoor_inputs(ref_image, ref_mask, tar_image, tar_mask):
    """AnyDoor 원본 process_pairs 기반 입력 전처리."""

    ref_box_yyxx = get_bbox_from_mask(ref_mask)

    ref_mask_3 = np.stack([ref_mask, ref_mask, ref_mask], -1)
    masked_ref_image = (
        ref_image * ref_mask_3
        + np.ones_like(ref_image) * 255 * (1 - ref_mask_3)
    )

    y1, y2, x1, x2 = ref_box_yyxx
    masked_ref_image = masked_ref_image[y1:y2, x1:x2, :]
    ref_mask = ref_mask[y1:y2, x1:x2]

    ratio = np.random.randint(12, 13) / 10
    masked_ref_image, ref_mask = expand_image_mask(
        masked_ref_image,
        ref_mask,
        ratio=ratio
    )

    ref_mask_3 = np.stack([ref_mask, ref_mask, ref_mask], -1)

    masked_ref_image = pad_to_square(
        masked_ref_image,
        pad_value=255,
        random=False
    )
    masked_ref_image = cv2.resize(
        masked_ref_image,
        (224, 224)
    ).astype(np.uint8)

    ref_mask_3 = pad_to_square(
        ref_mask_3 * 255,
        pad_value=0,
        random=False
    )
    ref_mask_3 = cv2.resize(
        ref_mask_3,
        (224, 224)
    ).astype(np.uint8)

    ref_mask = ref_mask_3[:, :, 0]

    masked_ref_image_aug = masked_ref_image

    masked_ref_image_compose = masked_ref_image
    ref_mask_compose = ref_mask

    masked_ref_image_aug = masked_ref_image_compose.copy()

    ref_image_collage = sobel(
        masked_ref_image_compose,
        ref_mask_compose / 255
    )

    tar_box_yyxx = get_bbox_from_mask(tar_mask)
    tar_box_yyxx = expand_bbox(
        tar_mask,
        tar_box_yyxx,
        ratio=[1.1, 1.2]
    )

    tar_box_yyxx_crop = expand_bbox(
        tar_image,
        tar_box_yyxx,
        ratio=[1.5, 3]
    )

    tar_box_yyxx_crop = box2squre(
        tar_image,
        tar_box_yyxx_crop
    )

    y1, y2, x1, x2 = tar_box_yyxx_crop

    cropped_target_image = tar_image[y1:y2, x1:x2, :]

    tar_box_yyxx = box_in_box(
        tar_box_yyxx,
        tar_box_yyxx_crop
    )

    y1, y2, x1, x2 = tar_box_yyxx

    ref_image_collage = cv2.resize(
        ref_image_collage,
        (x2 - x1, y2 - y1)
    )

    ref_mask_compose = cv2.resize(
        ref_mask_compose.astype(np.uint8),
        (x2 - x1, y2 - y1)
    )

    ref_mask_compose = (
        ref_mask_compose > 128
    ).astype(np.uint8)

    collage = cropped_target_image.copy()
    collage[y1:y2, x1:x2, :] = ref_image_collage

    collage_mask = cropped_target_image.copy() * 0.0
    collage_mask[y1:y2, x1:x2, :] = 1.0

    H1, W1 = collage.shape[0], collage.shape[1]

    cropped_target_image = pad_to_square(
        cropped_target_image,
        pad_value=0,
        random=False
    ).astype(np.uint8)

    collage = pad_to_square(
        collage,
        pad_value=0,
        random=False
    ).astype(np.uint8)

    collage_mask = pad_to_square(
        collage_mask,
        pad_value=-1,
        random=False
    ).astype(np.uint8)

    H2, W2 = collage.shape[0], collage.shape[1]

    cropped_target_image = cv2.resize(
        cropped_target_image,
        (512, 512)
    ).astype(np.float32)

    collage = cv2.resize(
        collage,
        (512, 512)
    ).astype(np.float32)

    collage_mask = (
        cv2.resize(
            collage_mask,
            (512, 512)
        ).astype(np.float32) > 0.5
    ).astype(np.float32)

    masked_ref_image_aug = masked_ref_image_aug / 255
    cropped_target_image = cropped_target_image / 127.5 - 1.0
    collage = collage / 127.5 - 1.0

    collage = np.concatenate(
        [collage, collage_mask[:, :, :1]],
        -1
    )

    item = dict(
        ref=masked_ref_image_aug.copy(),
        jpg=cropped_target_image.copy(),
        hint=collage.copy(),
        extra_sizes=np.array([H1, W1, H2, W2]),
        tar_box_yyxx_crop=np.array(tar_box_yyxx_crop)
    )

    return item



# 전처리된 입력으로 AnyDoor 합성 실행
def generate_with_anydoor(
    model,
    ddim_sampler,
    ref_image,
    ref_mask,
    tar_image,
    tar_mask,
    guidance_scale=5.0
):
    """AnyDoor 모델을 이용해 객체 합성을 수행한다."""

    # AnyDoor 입력 전처리
    item = process_anydoor_inputs(
        ref_image,
        ref_mask,
        tar_image,
        tar_mask
    )

    ref = item["ref"]
    hint = item["hint"]

    num_samples = 1

    # Detail 조건을 PyTorch Tensor로 변환
    control = torch.from_numpy(hint.copy()).float().cuda()
    control = torch.stack(
        [control for _ in range(num_samples)],
        dim=0
    )
    control = einops.rearrange(
        control,
        "b h w c -> b c h w"
    ).clone()

    # Reference 객체 정보를 PyTorch Tensor로 변환
    clip_input = torch.from_numpy(ref.copy()).float().cuda()
    clip_input = torch.stack(
        [clip_input for _ in range(num_samples)],
        dim=0
    )
    clip_input = einops.rearrange(
        clip_input,
        "b h w c -> b c h w"
    ).clone()

    
    # AnyDoor 생성 조건 설정
    guess_mode = False
    H, W = 512, 512

    cond = {
        "c_concat": [control],
        "c_crossattn": [
            model.get_learned_conditioning(clip_input)
        ]
    }

    un_cond = {
        "c_concat": None if guess_mode else [control],
        "c_crossattn": [
            model.get_learned_conditioning(
                [torch.zeros((1, 3, 224, 224))] * num_samples
            )
        ]
    }

    shape = (4, H // 8, W // 8)


    # DDIM Sampling 설정
    strength = 1
    ddim_steps = 50
    scale = guidance_scale
    eta = 0.0

    model.control_scales = [strength] * 13

    samples, intermediates = ddim_sampler.sample(
        ddim_steps,
        num_samples,
        shape,
        cond,
        verbose=False,
        eta=eta,
        unconditional_guidance_scale=scale,
        unconditional_conditioning=un_cond
    )

    # 생성된 Latent를 이미지로 변환
    x_samples = model.decode_first_stage(samples)

    x_samples = (
        einops.rearrange(
            x_samples,
            "b c h w -> b h w c"
        ) * 127.5 + 127.5
    ).cpu().numpy()

    pred = x_samples[0]
    pred = np.clip(pred, 0, 255)[1:, :, :]

    # 생성 결과를 원본 Target 이미지에 위치에 다시 삽입
    sizes = item["extra_sizes"]
    tar_box_yyxx_crop = item["tar_box_yyxx_crop"]

    gen_image = crop_anydoor_result(
        pred,
        tar_image,
        sizes,
        tar_box_yyxx_crop
    )

    return gen_image


# 생성된 영역을 원본 Target 이미지에 다시 합성
def crop_anydoor_result(pred, tar_image, extra_sizes, tar_box_yyxx_crop):
    """AnyDoor 생성 결과를 원래 Target 이미지 위치에 되돌린다."""

    H1, W1, H2, W2 = extra_sizes
    y1, y2, x1, x2 = tar_box_yyxx_crop

    pred = cv2.resize(pred, (W2, H2))

    m = 5

    if W1 == H1:
        tar_image[y1+m:y2-m, x1+m:x2-m, :] = pred[m:-m, m:-m]
        return tar_image

    if W1 < W2:
        pad1 = int((W2 - W1) / 2)
        pad2 = W2 - W1 - pad1
        pred = pred[:, pad1:-pad2, :]
    else:
        pad1 = int((H2 - H1) / 2)
        pad2 = H2 - H1 - pad1
        pred = pred[pad1:-pad2, :, :]

    gen_image = tar_image.copy()

    gen_image[y1+m:y2-m, x1+m:x2-m, :] = pred[m:-m, m:-m]

    return gen_image


# 파일 직접 실행 시 AnyDoor 합성 테스트
if __name__ == "__main__":
    print("AnyDoor 모델 로딩 시작")

    model, ddim_sampler = load_anydoor_model()

    print("AnyDoor 모델 로딩 완료")

    # 공식 AnyDoor TestDreamBooth 예제 경로
    reference_image_path = (
        ANYDOOR_ROOT / "examples" / "TestDreamBooth" / "FG" / "01.png"
    )

    bg_image_path = (
        ANYDOOR_ROOT / "examples" / "TestDreamBooth" / "BG"
        / "000000309203_GT.png"
    )

    bg_mask_path = (
        ANYDOOR_ROOT / "examples" / "TestDreamBooth" / "BG"
        / "000000309203_mask.png"
    )

    save_path = MOA_ROOT / "experiments" / "anydoor_wrapper_test.png"

    # Reference Image + Reference Mask
    image = cv2.imread(
        str(reference_image_path),
        cv2.IMREAD_UNCHANGED
    )

    ref_mask = (image[:, :, -1] > 128).astype(np.uint8)

    ref_image = image[:, :, :-1]
    ref_image = cv2.cvtColor(
        ref_image.copy(),
        cv2.COLOR_BGR2RGB
    )

    # Target Image
    tar_image = cv2.imread(
        str(bg_image_path)
    ).astype(np.uint8)

    tar_image = cv2.cvtColor(
        tar_image,
        cv2.COLOR_BGR2RGB
    )

    # Target Mask
    tar_mask = cv2.imread(
        str(bg_mask_path)
    )[:, :, 0]

    tar_mask = (tar_mask > 128).astype(np.uint8)

    print("AnyDoor 합성 시작")

    gen_image = generate_with_anydoor(
        model,
        ddim_sampler,
        ref_image,
        ref_mask,
        tar_image.copy(),
        tar_mask
    )

    # OpenCV 저장을 위해 RGB → BGR
    cv2.imwrite(
        str(save_path),
        gen_image[:, :, ::-1]
    )

    print("AnyDoor 합성 완료")
    print("결과 저장:", save_path)