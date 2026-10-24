"""AnyDoor 재학습 학습 (VITON-HD 새 학습 재료).

- 시작 가중치: --resume (기본 $ANYDOOR_DIR/checkpoints/epoch=1-step=8687.ckpt, 읽기만)
- 학습 부품: AnyDoor 원래 학습 설정과 같음 (ControlNet 전부, UNet 뒷부분, DINOv2 연결부 / sd_locked = False)
- 옵티마이저 AdamW, 학습률 --lr (기본 1e-5), 16비트 혼합 정밀도
- 학습 재료: retrain_dataset.VitonHDWide (<out_dir>/ids.txt의 쌍, retrain_ids.py로 생성)
- 여러 GPU: --gpus N (DDP), GPU당 한 번에 --batch장
- 저장: --save-every 스텝마다 <out_dir>/checkpoints/wide-step=N.ckpt (1개 약 10GB, 모두 보관), 0이면 저장 안 함
- 기록: 스텝마다 걸린 시간·손실·GPU 최대 메모리 (첫 GPU만 출력)

python retrain_train.py <out_dir> --steps 20 --save-every 0                     (동작 확인)
python retrain_train.py <out_dir> --steps 10000 --gpus 8 --batch 4 --save-every 2000
"""
import argparse
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("out_dir", help="결과 폴더 (ids.txt가 있어야 함)")
ap.add_argument("--steps", type=int, required=True)
ap.add_argument("--gpus", type=int, default=1)
ap.add_argument("--batch", type=int, default=1, help="GPU당 한 번에 학습할 사진 수")
ap.add_argument("--save-every", type=int, default=0, help="가중치 저장 간격 (스텝), 0이면 저장 안 함")
ap.add_argument("--lr", type=float, default=1e-5)
ap.add_argument("--workers", type=int, default=0 if os.name == "nt" else 4, help="학습 재료를 만드는 프로세스 수")
ap.add_argument("--resume", default=None, help="시작 가중치 (기본: AnyDoor 공식 가중치)")
a = ap.parse_args()

AD = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor")).resolve()
OUT = Path(a.out_dir).resolve()
sys.argv[0] = str(Path(__file__).resolve())  # 여러 GPU(DDP)에서 같은 명령을 다시 실행할 때 경로가 꼬이지 않게 절대 경로로
sys.argv[1] = str(OUT)
sys.path.insert(0, str(AD))
sys.path.insert(1, str(Path(__file__).resolve().parent))
os.chdir(AD)  # AnyDoor 코드가 ./dinov2, ./configs 상대 경로로 불러옴 (읽기만), 학습 직전에 결과 폴더로 이동

import numpy as np  # noqa: E402
import pytorch_lightning as pl  # noqa: E402
import torch  # noqa: E402
from pytorch_lightning.callbacks import ModelCheckpoint  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

from cldm.hack import disable_verbosity  # noqa: E402
from cldm.model import create_model, load_state_dict  # noqa: E402
from retrain_dataset import VitonHDWide  # noqa: E402

if os.name == "nt":  # 학습하는 동안만 Windows 절전 막기 (컴퓨터 설정은 그대로, 프로그램이 끝나면 저절로 풀림)
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

disable_verbosity()
ids = [line.split("\t")[0] for line in (OUT / "ids.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
resume = a.resume or str(AD / "checkpoints" / "epoch=1-step=8687.ckpt")
print(f"학습 쌍 {len(ids)}개, {a.steps}스텝, GPU {a.gpus}개 × {a.batch}장, 저장 간격 {a.save_every or '없음'}, 시작 가중치 {resume}",
      flush=True)

t0 = time.time()
model = create_model(str(AD / "configs" / "anydoor.yaml")).cpu()
model.load_state_dict(load_state_dict(resume, location="cpu"))
model.learning_rate = a.lr
model.sd_locked = False
model.only_mid_control = False
print(f"모델 불러오기 {time.time() - t0:.0f}초", flush=True)
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(OUT)  # 학습 기록이 AnyDoor 폴더에 생기지 않게


class Speed(pl.Callback):
    """스텝마다 걸린 시간·손실·GPU 최대 메모리 (첫 GPU만 출력)"""

    def __init__(self):
        self.t, self.times = 0.0, []

    def on_train_batch_start(self, trainer, pl_module, batch, batch_idx):
        torch.cuda.synchronize()
        self.t = time.time()

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        torch.cuda.synchronize()
        dt = time.time() - self.t
        self.times.append(dt)
        if trainer.is_global_zero:
            loss = outputs.get("loss") if isinstance(outputs, dict) else outputs
            loss = float(loss) if loss is not None else float("nan")
            print(f"스텝 {trainer.global_step}: {dt:.1f}초, 손실 {loss:.4f}, GPU 최대 {torch.cuda.max_memory_allocated() / 2**30:.1f}GB",
                  flush=True)

    def on_train_end(self, trainer, pl_module):
        if trainer.is_global_zero:
            t = self.times[2:] or self.times  # 처음 2스텝(준비 시간) 제외
            print(f"평균 {sum(t) / len(t):.2f}초/스텝 (처음 2스텝 제외), GPU 최대 {torch.cuda.max_memory_allocated() / 2**30:.1f}GB",
                  flush=True)


def seed_worker(_):
    np.random.seed(torch.initial_seed() % 2**32)  # 학습 재료 프로세스마다 다른 무작위 값 (크롭 배율, 학습 시점)


callbacks = [Speed()]
if a.save_every > 0:
    callbacks.append(ModelCheckpoint(dirpath=str(OUT / "checkpoints"), filename="wide-{step}", save_top_k=-1,
                                     save_weights_only=True, every_n_train_steps=a.save_every))
trainer = pl.Trainer(accelerator="gpu", devices=a.gpus, strategy="ddp" if a.gpus > 1 else None, precision=16,
                     max_steps=a.steps, callbacks=callbacks, enable_checkpointing=a.save_every > 0, logger=False,
                     default_root_dir=str(OUT), enable_progress_bar=False)
loader = DataLoader(VitonHDWide(ids), batch_size=a.batch, shuffle=True, num_workers=a.workers,
                    worker_init_fn=seed_worker, persistent_workers=a.workers > 0)
t1 = time.time()
trainer.fit(model, loader)
if trainer.is_global_zero:
    print(f"학습 {time.time() - t1:.0f}초, 전체 {time.time() - t0:.0f}초", flush=True)
