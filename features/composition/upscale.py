"""합성 결과 초해상도 복원: Real-ESRGAN x2plus, RRDBNet 구조.

- 문제: AnyDoor는 학습 해상도 512로 그린 뒤 다시 그린 정사각형 크기로 키운다. 정사각형이 890~930px이면 1.7~1.8배 확대라
  새 상의 미세 질감이 같은 크기로 맞춘 상품 사진의 74~90%에 그쳐, 원본을 그대로 쓰는 머리만 선명해 보였다
- 방법: 512 결과를 2배 초해상도로 1024 복원한 뒤 정사각형 크기로 줄여 붙인다. 확대가 축소로 바뀐다
  anydoor_composer가 AnyDoor crop_back 앞에 끼워 넣어 사용, 정사각형이 512보다 클 때만 적용
- 시험 2026-11-10: 모델 원래 결과 6장, 새 상의 미세 질감 0.71~1.00 → 1.21~1.55, 상품 사진 같은 크기 기준 0.96~1.06.
  512 → 1024 처리 0.2~0.4초, GPU 메모리 최고 578MiB, 16비트
- 가중치: RealESRGAN_x2plus.pth, Real-ESRGAN 공식 릴리스 v0.2.1, SHA-256 49fafd45...6abb.
  torch.load(weights_only=True)로 가중치 값만 읽어 파일 안 코드 실행 없음. 패키지 설치 없이 네트워크 구조만 직접 작성
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualDenseBlock(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(nf, gc)
        self.rdb2 = ResidualDenseBlock(nf, gc)
        self.rdb3 = ResidualDenseBlock(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    """2배 초해상도: 입력을 pixel unshuffle로 절반 크기 12채널로 바꾼 뒤 4배 확대해 전체 2배"""

    def __init__(self, nf=64, nb=23, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(12, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(F.pixel_unshuffle(x, 2))
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


class Upscaler:
    """2배 초해상도 복원기. 처음 만들 때 가중치를 GPU에 적재하고 이후 재사용"""

    def __init__(self, path, device="cuda", half=True):
        state = torch.load(path, map_location="cpu", weights_only=True)  # 가중치 값만 읽음
        state = state.get("params_ema", state.get("params", state))
        net = RRDBNet()
        net.load_state_dict(state, strict=True)
        net.eval().to(device)
        self.half = half
        self.net = net.half() if half else net
        self.device = device

    @torch.no_grad()
    def __call__(self, rgb):
        """RGB uint8 (H, W, 3), H·W 짝수 → RGB uint8 (2H, 2W, 3)"""
        x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1))).to(self.device).float().div(255).unsqueeze(0)
        if self.half:
            x = x.half()
        y = self.net(x).float().clamp(0, 1)[0].permute(1, 2, 0).cpu().numpy()
        return (y * 255).round().astype(np.uint8)
