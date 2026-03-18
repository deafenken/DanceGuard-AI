import numpy as np
import mindspore.dataset as ds


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


def fake_data(n: int = 100, t: int = 64, j: int = 24, seed: int = 7):
    rng = np.random.default_rng(seed)
    mocap = rng.normal(0.0, 1.0, size=(n, t, j, 3)).astype(np.float32)
    label = rng.uniform(55.0, 98.0, size=(n,)).astype(np.float32)
    return mocap, label
