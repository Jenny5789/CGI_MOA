"""모델 추론 서버 동작 확인용 요청 스크립트. 표준 라이브러리와 OpenCV·NumPy만 사용.

사용: 저장소 최상위 폴더에서
    python model_server/test_client.py http://127.0.0.1:8100 결과폴더 [토큰]

순서: /health 확인 → 상품 사진 이미지 분할 → 모델 사진 합성 영역 생성 → 이미지 합성
입력: generated_assets 예시 사진 top_001·model_001
출력: 결과폴더의 garment_mask.png, area.png, result.png
"""
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CRLF = "\r\n"


def post(url, headers, data=None, files=None, timeout=600):
    """multipart 요청 전송. 응답 본문과 헤더 반환"""
    b = uuid.uuid4().hex
    parts = []
    for k, v in (data or {}).items():
        parts.append(f'--{b}{CRLF}Content-Disposition: form-data; name="{k}"{CRLF}{CRLF}{v}{CRLF}'.encode())
    for k, path in (files or {}).items():
        head = (f'--{b}{CRLF}Content-Disposition: form-data; name="{k}"; filename="{Path(path).name}"{CRLF}'
                f"Content-Type: image/png{CRLF}{CRLF}")
        parts.append(head.encode() + Path(path).read_bytes() + CRLF.encode())
    parts.append(f"--{b}--{CRLF}".encode())
    req = urllib.request.Request(url, data=b"".join(parts), method="POST",
                                 headers={**headers, "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers


def main():
    url, out = sys.argv[1].rstrip("/"), Path(sys.argv[2])
    headers = {"X-Model-Token": sys.argv[3]} if len(sys.argv) > 3 else {}
    out.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(f"{url}/health", timeout=10) as r:
        health = json.loads(r.read())
    print("상태:", json.dumps(health, ensure_ascii=False))
    if health["status"] != "ready":
        sys.exit("모델 준비 전, 잠시 후 다시 실행")

    garment = ROOT / "generated_assets/tops_only_30/top_001.png"
    person = ROOT / "generated_assets/base_models_30/model_001.png"

    t = time.time()
    content, h = post(f"{url}/extract", headers, data={"points": json.dumps([[627, 600]])}, files={"image": garment})
    (out / "garment_mask.png").write_bytes(content)
    print(f"상품 이미지 분할: {time.time() - t:.1f}초, 서버 처리 {h['X-Elapsed-Sec']}초")

    content, h = post(f"{url}/extract", headers, data={"points": json.dumps([[627, 640]])}, files={"image": person})
    top = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_GRAYSCALE) > 127
    ys, xs = np.nonzero(top)
    dy, dx = int((ys.max() - ys.min()) * 0.08), int((xs.max() - xs.min()) * 0.08)
    area = np.zeros(top.shape, np.uint8)
    area[max(ys.min() - dy, 0):ys.max() + dy, max(xs.min() - dx, 0):xs.max() + dx] = 255
    cv2.imwrite(str(out / "area.png"), area)

    t = time.time()
    content, h = post(f"{url}/compose", headers, data={"seed": 1234},
                      files={"garment": garment, "garment_mask": out / "garment_mask.png", "person": person,
                             "area": out / "area.png"})
    (out / "result.png").write_bytes(content)
    print(f"이미지 합성: {time.time() - t:.1f}초, 서버 처리 {h['X-Elapsed-Sec']}초, 다시 그린 영역 {h['X-Crop-Box']}")
    print("저장:", out)


if __name__ == "__main__":
    main()
