"""GPU 차례 지키기.

GPU(RTX 3080 10GB)가 하나뿐이라 SAM2 추출과 합성이 동시에 돌면 메모리가 부족할 수 있다.
GPU를 쓰는 작업은 `with GPU_LOCK:` 안에서만 실행해 한 번에 하나씩 처리한다.
"""
import threading

GPU_LOCK = threading.Lock()


def release_cached_memory():
    """GPU 작업(추출·합성)이 끝나면 PyTorch가 잡아 두고 안 쓰는 GPU 메모리를 돌려준다.
    PyTorch는 다 쓴 메모리도 다음을 위해 잡아 두는데, SAM2와 AnyDoor가 번갈아 쓰면서 잡아 둔 양이 쌓이면 10GB를 넘어
    넘친 만큼 본체 RAM(공유 GPU 메모리)을 쓰고 합성이 느려진다 (10/17 확인: 서버 전용 9.4GB + 공유 2.8GB).
    모델 가중치는 그대로 두므로 다음 작업 속도에는 영향이 거의 없다"""
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # GPU가 없거나 torch를 못 불러와도 서버는 계속
        pass
