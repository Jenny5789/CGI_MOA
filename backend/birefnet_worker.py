# backend/birefnet_worker.py
# BiRefNet(정밀 재분할) 전용 자식 프로세스.
#
# 왜 별도 프로세스인가:
#   BiRefNet은 최신 transformers/torch(venv_libcom, torch 2.6)를 요구하고,
#   백엔드 본체는 SAM/AnyDoor 때문에 torch 2.0(venv)에 묶여 있다.
#   두 버전을 한 프로세스에 같이 올릴 수 없어서, 백엔드가 이 파일을
#   venv_libcom 의 파이썬으로 띄워두고 표준입출력으로 대화한다.
#   프로세스를 계속 살려두므로 모델 로딩은 최초 1회만 일어난다.
#
# 프로토콜 (한 줄에 JSON 하나):
#   요청  {"src": "원본이미지경로", "bbox": [x0,y0,x1,y1], "out": "결과마스크저장경로"}
#   응답  {"ok": true}  또는  {"ok": false, "error": "..."}
#   종료  빈 줄 / EOF

import json
import sys

import cv2
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModelForImageSegmentation

MODEL_ID = "ZhengPeng7/BiRefNet"
INPUT_SIZE = 1024        # BiRefNet 학습 해상도

_model = None
_device = None
_transform = None


def _log(msg: str):
    """진단용 로그는 stderr 로만 보낸다(stdout 은 응답 전용이라 섞이면 안 됨)."""
    print(f"[birefnet] {msg}", file=sys.stderr, flush=True)


def _load_model():
    global _model, _device, _transform
    if _model is not None:
        return

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _log(f"모델 로딩 시작 (device={_device})")
    model = AutoModelForImageSegmentation.from_pretrained(MODEL_ID, trust_remote_code=True)
    model.to(_device).eval()
    if _device == "cuda":
        model.half()               # VRAM 절약 (10GB 카드에서 SAM 과 공존해야 함)
    _model = model

    _transform = T.Compose([
        T.Resize((INPUT_SIZE, INPUT_SIZE)),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    _log("모델 로딩 완료")


def _refine(src_path: str, bbox: list[int], out_path: str):
    """
    bbox 로 잘라낸 영역만 BiRefNet 에 넣고, 결과 알파를 원본 좌표계로 되돌려 저장한다.
    잘라서 넣는 이유: BiRefNet 은 점/박스 프롬프트를 받지 않고 '화면에서 두드러진 물체'를
    찾는 모델이라, 대상만 크롭해서 넣어야 그 물체를 집는다.
    """
    src = cv2.imread(src_path)
    if src is None:
        raise RuntimeError(f"원본 이미지를 읽을 수 없음: {src_path}")
    h, w = src.shape[:2]

    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise RuntimeError(f"crop 영역이 너무 작음: {bbox}")

    crop_rgb = cv2.cvtColor(src[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
    inp = _transform(Image.fromarray(crop_rgb)).unsqueeze(0).to(_device)
    if _device == "cuda":
        inp = inp.half()

    with torch.no_grad():
        pred = _model(inp)[-1].sigmoid().cpu()[0].squeeze().float().numpy()

    alpha_crop = cv2.resize(pred, (x1 - x0, y1 - y0))
    alpha_full = np.zeros((h, w), dtype=np.uint8)
    alpha_full[y0:y1, x0:x1] = np.clip(alpha_crop * 255, 0, 255).astype(np.uint8)

    if not cv2.imwrite(out_path, alpha_full):
        raise RuntimeError(f"결과 저장 실패: {out_path}")


def main():
    _load_model()
    print(json.dumps({"ok": True, "ready": True}), flush=True)   # 준비 완료 신호

    for line in sys.stdin:
        line = line.strip()
        if not line:
            break
        try:
            req = json.loads(line)
            _refine(req["src"], req["bbox"], req["out"])
            print(json.dumps({"ok": True}), flush=True)
        except Exception as e:                                    # 한 건 실패로 죽지 않는다
            _log(f"처리 실패: {e}")
            print(json.dumps({"ok": False, "error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
