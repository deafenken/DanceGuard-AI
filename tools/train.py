import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import mindspore as ms

from app.model import DanceSet, EvalNet, fake_data, train_epoch


def main():
    ms.set_context(mode=ms.PYNATIVE_MODE)
    mocap, score = fake_data(n=100, t=64, j=24, seed=7)
    ds = DanceSet(mocap, score).to_ds(batch_size=8, shuffle=True)
    net = EvalNet(joints=24)
    train_epoch(net, ds, lr=1e-3, ckpt_path="assets/weights/best_dance_scoring.ckpt")


if __name__ == "__main__":
    main()


