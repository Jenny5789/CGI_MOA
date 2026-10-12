# backend/harmonize_worker.py
# PCTNet(이미지 하모나이제이션) 전용 자식 프로세스.
#
# 왜 별도 프로세스인가:
#   libcom 은 torch 2.6(venv_libcom)을 요구하고, 백엔드 본체는 SAM 때문에
#   torch 2.0(venv)에 묶여 있다. birefnet_worker.py 와 같은 이유·같은 방식이다.
#
# PCTNet 이 하는 일:
#   '이미 붙여놓은 합성 이미지'와 '앞쪽 객체 영역 마스크'를 받아서, 객체 쪽 색감·톤을
#   배경 환경에 맞게 조정한 이미지를 돌려준다. 픽셀을 새로 생성하는 게 아니라
#   원본 해상도 그대로 색만 옮기므로 디테일이 뭉개지지 않는다.
#
# 프로토콜 (한 줄에 JSON 하나):
#   요청  {"comp": "합성이미지경로", "mask": "객체영역마스크경로", "out": "결과저장경로"}
#   응답  {"ok": true}  또는  {"ok": false, "error": "..."}
#   종료  빈 줄 / EOF

import json
import os
import sys

# libcom 이 끌어오는 pytorch_lightning 등이 stdout 에 로그를 찍는다. stdout 은 응답 전용
# 채널이라 한 줄이라도 섞이면 부모가 JSON 파싱에 실패한다. 그래서 라이브러리를 import 하기
# 전에 진짜 stdout 을 따로 빼두고, sys.stdout 자체는 stderr 로 돌려놓는다.
_RESPONSE_OUT = sys.stdout
sys.stdout = sys.stderr

import cv2                                          # noqa: E402
import numpy as np                                  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# libcom 은 import 시점에 model_dir 을 확정하므로, import 전에 지정해야 한다.
# 이 경로 아래 pretrained_models/{PCTNet.pth, IdentityLUT33.txt} 가 있어야 다운로드를 건너뛴다.
os.environ.setdefault("LIBCOM_MODEL_DIR", os.path.join(BASE_DIR, "libcom_models"))

import torch                                        # noqa: E402
from libcom import ImageHarmonizationModel          # noqa: E402

_model = None


def _log(msg: str):
    """진단 로그는 stderr 로만 보낸다."""
    print(f"[pctnet] {msg}", file=sys.stderr, flush=True)


def _respond(payload: dict):
    """프로토콜 응답은 따로 빼둔 진짜 stdout 으로만 내보낸다."""
    _RESPONSE_OUT.write(json.dumps(payload) + "\n")
    _RESPONSE_OUT.flush()


def _load_model():
    global _model
    if _model is not None:
        return

    device = 0 if torch.cuda.is_available() else "cpu"
    _log(f"PCTNet 로딩 시작 (device={device}, model_dir={os.environ['LIBCOM_MODEL_DIR']})")
    _model = ImageHarmonizationModel(device=device, model_type="PCTNet")
    _log("PCTNet 로딩 완료")


def _harmonize(comp_path: str, mask_path: str, out_path: str):
    comp = cv2.imread(comp_path)
    if comp is None:
        raise RuntimeError(f"합성 이미지를 읽을 수 없음: {comp_path}")
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise RuntimeError(f"마스크를 읽을 수 없음: {mask_path}")
    if mask.shape[:2] != comp.shape[:2]:
        raise RuntimeError(f"마스크 크기 불일치: {mask.shape[:2]} vs {comp.shape[:2]}")
    if mask.max() == 0:
        raise RuntimeError("마스크가 비어 있음")

    result = _model(comp, mask)

    # PCTNet 경로의 outputs_postprocess 는 float 배열을 그대로 돌려준다(LBM 경로와 달리
    # uint8 캐스팅이 없음). 그대로 imwrite 하면 깨지므로 여기서 변환한다.
    result = np.clip(result, 0, 255).astype(np.uint8)

    if not cv2.imwrite(out_path, result):
        raise RuntimeError(f"결과 저장 실패: {out_path}")


def main():
    try:
        _load_model()
    except Exception as e:
        _log(f"모델 로딩 실패: {e}")
        _respond({"ok": False, "ready": False, "error": str(e)})
        return

    _respond({"ok": True, "ready": True})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            break
        try:
            req = json.loads(line)
            _harmonize(req["comp"], req["mask"], req["out"])
            _respond({"ok": True})
        except Exception as e:                       # 한 건 실패로 죽지 않는다
            _log(f"처리 실패: {e}")
            _respond({"ok": False, "error": str(e)})


if __name__ == "__main__":
    main()
