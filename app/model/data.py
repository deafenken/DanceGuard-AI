import os
from dataclasses import dataclass
from typing import Dict, Tuple

import mindspore.dataset as ds
import numpy as np

from .bvh_io import load_bvh_as_mocap
from .runtime import Scorer


def _resample_sequence(seq: np.ndarray, target_len: int) -> np.ndarray:
    seq = np.asarray(seq, dtype=np.float32)
    if len(seq) == target_len:
        return seq
    if len(seq) == 0:
        raise ValueError("sequence is empty")
    x_old = np.arange(len(seq), dtype=np.float32)
    x_new = np.linspace(0, len(seq) - 1, target_len, dtype=np.float32)
    out = np.empty((target_len, seq.shape[1], seq.shape[2]), dtype=np.float32)
    for j in range(seq.shape[1]):
        for a in range(seq.shape[2]):
            out[:, j, a] = np.interp(x_new, x_old, seq[:, j, a])
    return out


def _normalize_skeleton(seq: np.ndarray) -> np.ndarray:
    seq = np.asarray(seq, dtype=np.float32).copy()
    if seq.ndim != 3 or seq.shape[-1] != 3:
        raise ValueError("sequence shape must be [T, J, 3]")
    seq -= seq[:, :1, :]
    head = np.linalg.norm(seq[:, 4, :], axis=1)
    lf = np.linalg.norm(seq[:, 7, :], axis=1)
    rf = np.linalg.norm(seq[:, 11, :], axis=1)
    body_scale = np.maximum(np.median((head + lf + rf) / 3.0), 1e-3)
    seq /= body_scale
    return seq.astype(np.float32)


@dataclass
class DanceStandard:
    dance_type: str
    path: str
    sequence: np.ndarray


class DanceSet:
    """MoCap 主模态数据集，视觉模态缺失时使用零填充占位。"""

    def __init__(self, mocap: np.ndarray, score: np.ndarray):
        if mocap.ndim != 4 or mocap.shape[-1] != 3:
            raise ValueError("mocap shape must be [N, T, J, 3]")
        if score.ndim != 1 or score.shape[0] != mocap.shape[0]:
            raise ValueError("score shape must be [N]")
        self.mocap = mocap.astype(np.float32)
        self.score = score.astype(np.float32)
        self.frames = mocap.shape[1]

    def __len__(self):
        return self.mocap.shape[0]

    def __getitem__(self, idx):
        m = self.mocap[idx]
        # Zero-Padding 缺失模态插补：保持维度对齐，触发残差分支的自适应优雅降级。
        rgb = np.zeros((self.frames, 3, 224, 224), dtype=np.float32)
        flow = np.zeros((self.frames, 2, 224, 224), dtype=np.float32)
        y = np.float32(self.score[idx])
        return m, rgb, flow, y

    def to_ds(self, batch_size: int = 8, shuffle: bool = True):
        return ds.GeneratorDataset(
            source=self,
            column_names=["mocap", "rgb", "flow", "label"],
            shuffle=shuffle,
            python_multiprocessing=False,
        ).batch(batch_size, drop_remainder=False)


class BvhDatasetBuilder:
    """从标准 BVH 构造伪多模态训练集。真实输入只有骨架，视觉模态走缺失插补。"""

    def __init__(self, standards: Dict[str, str], seq_len: int = 64, joints: int = 24, seed: int = 7):
        self.seq_len = seq_len
        self.joints = joints
        self.rng = np.random.default_rng(seed)
        self.standards = self._load_standards(standards)
        if not self.standards:
            raise ValueError("no valid BVH standards found")
        self.scorers = {standard.dance_type: Scorer(dance_type=standard.dance_type, ckpt_path="", joints=self.joints, seq_len=self.seq_len) for standard in self.standards}

    def _load_standards(self, standards: Dict[str, str]):
        loaded = []
        for dance_type, path in standards.items():
            if not path or not os.path.exists(path):
                continue
            seq = load_bvh_as_mocap(path, joints=self.joints)
            seq = _normalize_skeleton(seq)
            loaded.append(DanceStandard(dance_type=dance_type, path=path, sequence=seq))
        return loaded

    def _random_window(self, seq: np.ndarray) -> np.ndarray:
        if len(seq) <= self.seq_len:
            return _resample_sequence(seq, self.seq_len)
        span = int(self.rng.integers(self.seq_len, min(len(seq), self.seq_len * 2) + 1))
        start_max = max(len(seq) - span, 1)
        start = int(self.rng.integers(0, start_max))
        return seq[start : start + span]

    def _augment(self, seq: np.ndarray) -> Tuple[np.ndarray, float]:
        tempo = float(self.rng.uniform(0.88, 1.12))
        amp = float(self.rng.uniform(0.92, 1.08))
        noise_sigma = float(self.rng.uniform(0.002, 0.035))
        jitter_sigma = float(self.rng.uniform(0.0, 0.018))
        drift_sigma = float(self.rng.uniform(0.0, 0.012))

        warped_len = max(16, int(round(len(seq) * tempo)))
        aug = _resample_sequence(seq, warped_len)
        aug = _resample_sequence(aug, self.seq_len)
        aug *= amp
        aug += self.rng.normal(0.0, noise_sigma, size=aug.shape).astype(np.float32)

        if jitter_sigma > 0:
            jitter = self.rng.normal(0.0, jitter_sigma, size=(self.seq_len, 1, 3)).astype(np.float32)
            aug += jitter
        if drift_sigma > 0:
            drift = self.rng.normal(0.0, drift_sigma, size=(1, aug.shape[1], 3)).astype(np.float32)
            aug += drift

        severe = self.rng.random() < 0.18
        if severe:
            joint_idx = int(self.rng.integers(4, min(21, aug.shape[1])))
            aug[:, joint_idx, :] += self.rng.normal(0.0, 0.08, size=(self.seq_len, 3)).astype(np.float32)

        return aug.astype(np.float32)

    def build_arrays(self, samples_per_dance: int = 600, include_reference: int = 40):
        motions = []
        labels = []
        meta = []
        for standard in self.standards:
            for _ in range(include_reference):
                ref = _resample_sequence(standard.sequence, self.seq_len)
                motions.append(ref.astype(np.float32))
                labels.append(100.0)
                meta.append(standard.dance_type)
            scorer = self.scorers[standard.dance_type]
            for _ in range(samples_per_dance):
                window = self._random_window(standard.sequence)
                aug = self._augment(window)
                score = float(scorer.score_mocap_sequence(aug)["final"])
                motions.append(aug)
                labels.append(score)
                meta.append(standard.dance_type)
        x = np.stack(motions, axis=0).astype(np.float32)
        y = np.asarray(labels, dtype=np.float32)
        return x, y, meta

    def build_dataset(self, samples_per_dance: int = 600, include_reference: int = 40, batch_size: int = 8, shuffle: bool = True):
        mocap, score, _ = self.build_arrays(samples_per_dance=samples_per_dance, include_reference=include_reference)
        return DanceSet(mocap, score).to_ds(batch_size=batch_size, shuffle=shuffle)


def build_bvh_training_data(standards: Dict[str, str], samples_per_dance: int = 600, seq_len: int = 64, joints: int = 24, seed: int = 7):
    builder = BvhDatasetBuilder(standards=standards, seq_len=seq_len, joints=joints, seed=seed)
    return builder.build_arrays(samples_per_dance=samples_per_dance)


def fake_data(n: int = 100, t: int = 64, j: int = 24, seed: int = 7):
    rng = np.random.default_rng(seed)
    mocap = rng.normal(0.0, 1.0, size=(n, t, j, 3)).astype(np.float32)
    label = rng.uniform(55.0, 98.0, size=(n,)).astype(np.float32)
    return mocap, label
