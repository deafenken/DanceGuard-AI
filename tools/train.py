import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import mindspore as ms
import numpy as np

from app.model import BvhDatasetBuilder, DanceSet, EvalNet, fake_data
from app.model.runtime import DANCE_KARA, DANCE_MUQAM
from app.model.train import eval_epoch, train_epoch


STANDARD_BVHS = {
    DANCE_KARA: os.path.join(ROOT_DIR, "Kara Jorga.bvh"),
    DANCE_MUQAM: os.path.join(ROOT_DIR, "Muqam.bvh"),
}


def build_train_val_datasets(batch_size: int, samples_per_dance: int, seq_len: int = 64, joints: int = 24, val_ratio: float = 0.1):
    if all(os.path.exists(path) for path in STANDARD_BVHS.values()):
        builder = BvhDatasetBuilder(STANDARD_BVHS, seq_len=seq_len, joints=joints, seed=7)
        mocap, score, meta = builder.build_arrays(samples_per_dance=samples_per_dance, include_reference=32)
        meta = np.asarray(meta)
        train_idx = []
        val_idx = []
        rng = np.random.default_rng(13)
        for dance_type in np.unique(meta):
            idx = np.where(meta == dance_type)[0]
            rng.shuffle(idx)
            split = max(1, int(round(len(idx) * (1.0 - val_ratio))))
            split = min(split, len(idx) - 1) if len(idx) > 1 else len(idx)
            train_idx.extend(idx[:split].tolist())
            val_idx.extend(idx[split:].tolist())
        train_idx = np.asarray(train_idx, dtype=np.int32)
        val_idx = np.asarray(val_idx, dtype=np.int32)
        train_ds = DanceSet(mocap[train_idx], score[train_idx]).to_ds(batch_size=batch_size, shuffle=True)
        val_ds = DanceSet(mocap[val_idx], score[val_idx]).to_ds(batch_size=batch_size, shuffle=False)
        print(f"use_bvh_dataset=True, train={len(train_idx)}, val={len(val_idx)}, standards={list(STANDARD_BVHS.values())}, samples_per_dance={samples_per_dance}")
        return train_ds, val_ds

    mocap, score = fake_data(n=100, t=seq_len, j=joints, seed=7)
    split = int(round(len(mocap) * 0.9))
    print("use_bvh_dataset=False, fallback=fake_data")
    train_ds = DanceSet(mocap[:split], score[:split]).to_ds(batch_size=batch_size, shuffle=True)
    val_ds = DanceSet(mocap[split:], score[split:]).to_ds(batch_size=batch_size, shuffle=False)
    return train_ds, val_ds


def main():
    parser = argparse.ArgumentParser(description='基于标准 BVH 构建 MindSpore 训练集并训练评分网络')
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--samples-per-dance', type=int, default=320)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--val-ratio', type=float, default=0.1)
    parser.add_argument('--ckpt', default=os.path.join(ROOT_DIR, 'assets', 'weights', 'best_dance_scoring.ckpt'))
    args = parser.parse_args()

    ms.set_context(mode=ms.PYNATIVE_MODE)
    os.makedirs(os.path.dirname(args.ckpt), exist_ok=True)

    train_ds, val_ds = build_train_val_datasets(
        batch_size=args.batch_size,
        samples_per_dance=args.samples_per_dance,
        val_ratio=args.val_ratio,
    )
    net = EvalNet(joints=24)
    best_val = float('inf')

    for epoch in range(1, args.epochs + 1):
        print(f"epoch={epoch}/{args.epochs}")
        train_loss = train_epoch(net, train_ds, lr=args.lr, ckpt_path=args.ckpt + '.last')
        val_loss = eval_epoch(net, val_ds)
        print(f"val_loss={val_loss:.6f}")
        if val_loss <= best_val:
            best_val = val_loss
            ms.save_checkpoint(net, args.ckpt)
            print(f"best_ckpt={args.ckpt}, best_val={best_val:.6f}")
        else:
            print(f"keep_best={args.ckpt}, best_val={best_val:.6f}")

    print(f"final_ckpt={args.ckpt}")


if __name__ == "__main__":
    main()
