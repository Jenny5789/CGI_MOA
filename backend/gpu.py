"""GPU 차례 지키기.

GPU(RTX 3080 10GB)가 하나뿐이라 SAM2 추출과 합성이 동시에 돌면 메모리가 부족할 수 있다.
GPU를 쓰는 작업은 `with GPU_LOCK:` 안에서만 실행해 한 번에 하나씩 처리한다.
"""
import threading

GPU_LOCK = threading.Lock()
