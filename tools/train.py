import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import mindspore as ms

from app.model import BvhDatasetBuilder, DanceSet, EvalNet, fake_data, train_epoch


STANDARD_BVHS = {
    "黑走马 (Kara Jorga)": os.path.join(ROOT_DIR, "Kara Jorga.bvh"),
    "木卡姆 (Muqam)": os.path.join(ROOT_DIR, "Muqam.bvh"),
}


def build_dataset(batch_size: int, samples_per_dance: int, seq_len: int = 64, joints: int = 24):
    if all(os.path.exists(path) for path in STANDARD_BVHS.values()):
        builder = BvhDatasetBuilder(STANDARD_BVHS, seq_len=seq_len, joints=joints, seed=7)
        ds = builder.build_dataset(samples_per_dance=samples_per_dance, include_reference=32, batch_size=batch_size, shuffle=True)
        print(f"use_bvh_dataset=True, standards={list(STANDARD_BVHS.values())}, samples_per_dance={samples_per_dance}")
        return ds

    mocap, score = fake_data(n=100, t=seq_len, j=joints, seed=7)
    print("use_bvh_dataset=False, fallback=fake_data")
    return DanceSet(mocap, score).to_ds(batch_size=batch_size, shuffle=True)


def main():
    parser = argparse.ArgumentParser(description='基于标准 BVH 的 MindSpore 训练入口')
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--samples-per-dance', type=int, default=320)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--ckpt', default=os.path.join(ROOT_DIR, 'assets', 'weights', 'best_dance_scoring.ckpt'))
    args = parser.parse_args()

    ms.set_context(mode=ms.PYNATIVE_MODE)
    os.makedirs(os.path.dirname(args.ckpt), exist_ok=True)

    ds = build_dataset(batch_size=args.batch_size, samples_per_dance=args.samples_per_dance)
    net = EvalNet(joints=24)

    for epoch in range(1, args.epochs + 1):
        print(f"epoch={epoch}/{args.epochs}")
        train_epoch(net, ds, lr=args.lr, ckpt_path=args.ckpt)

    print(f"final_ckpt={args.ckpt}")


if __name__ == "__main__":
    main()
