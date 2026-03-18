import os
import random
import time
from collections import deque
from typing import Dict, Optional, Tuple

import numpy as np

from .infer import load_model, predict


class Scorer:
    """实时与离线共用的评分器。MoCap 为主输入，RGB/Flow 仅保留网络拓扑。"""

    def __init__(
        self,
        dance_type: str,
        ckpt_path: str = "assets/weights/best_dance_scoring.ckpt",
        joints: int = 24,
        seq_len: int = 64,
    ):
        self.dance_type = dance_type
        self.joints = joints
        self.seq_len = seq_len
        self.buffer = deque(maxlen=seq_len)
        self.last_t = 0.0
        self.interval = 0.25

        self.model = None
        if os.path.exists(ckpt_path):
            try:
                self.model = load_model(ckpt_path, joints=joints)
            except Exception:
                self.model = None

        self.feedback_pool = [
            "手臂线条很好，继续保持。",
            "注意髋部带动和重心转移。",
            "节奏很稳，动作衔接顺畅。",
            "上肢幅度可以再打开一些。",
            "脚步落点略有偏移，注意站位。",
            "动作完成度不错，保持稳定输出。",
        ]

    def _frame_to_mocap_like(self, frame_rgb: np.ndarray) -> np.ndarray:
        small = frame_rgb[::16, ::16, :]
        mean_rgb = np.mean(small, axis=(0, 1), dtype=np.float32)
        std_rgb = np.std(small, axis=(0, 1), dtype=np.float32)
        seed = np.concatenate([mean_rgb, std_rgb]).astype(np.float32)
        feat = np.resize(seed, self.joints * 3).astype(np.float32)
        return feat.reshape(self.joints, 3)

    def _mock(self) -> Tuple[int, str]:
        if self.dance_type == "黑走马 (Kara Jorga)":
            score = int(max(70, min(98, random.gauss(90, 4))))
        else:
            score = int(max(55, min(97, random.gauss(80, 11))))
        return score, random.choice(self.feedback_pool)

    def _normalize_sequence_shape(self, mocap_seq: np.ndarray) -> np.ndarray:
        seq = np.asarray(mocap_seq, dtype=np.float32)
        if seq.ndim != 3 or seq.shape[-1] != 3:
            raise ValueError("mocap_seq shape must be [T, J, 3]")
        if seq.shape[1] < self.joints:
            pad = np.zeros((seq.shape[0], self.joints - seq.shape[1], 3), dtype=np.float32)
            seq = np.concatenate([seq, pad], axis=1)
        elif seq.shape[1] > self.joints:
            seq = seq[:, : self.joints, :]
        return seq

    def _resample_sequence(self, mocap_seq: np.ndarray) -> np.ndarray:
        seq = self._normalize_sequence_shape(mocap_seq)
        if len(seq) == self.seq_len:
            return seq
        if len(seq) == 0:
            return np.zeros((self.seq_len, self.joints, 3), dtype=np.float32)
        idx = np.linspace(0, len(seq) - 1, self.seq_len)
        base = np.arange(len(seq), dtype=np.float32)
        out = np.empty((self.seq_len, self.joints, 3), dtype=np.float32)
        for joint in range(self.joints):
            for axis in range(3):
                out[:, joint, axis] = np.interp(idx, base, seq[:, joint, axis])
        return out

    def _heuristic_sequence_score(self, mocap_seq: np.ndarray) -> Dict[str, float]:
        seq = self._normalize_sequence_shape(mocap_seq)
        if len(seq) < 2:
            return {"base": 72.0, "residual": 0.0, "final": 72.0}
        velocity = np.linalg.norm(np.diff(seq, axis=0), axis=-1)
        motion_energy = float(np.mean(velocity))
        stability = float(np.std(velocity))
        if self.dance_type == "黑走马 (Kara Jorga)":
            base = 90.0 - stability * 15.0 + motion_energy * 4.0
        else:
            base = 84.0 - stability * 10.0 + motion_energy * 6.0
        residual = float(np.clip((motion_energy - stability) * 0.8, -2.0, 2.0))
        final = float(np.clip(base + residual, 0.0, 100.0))
        return {"base": float(np.clip(base, 0.0, 100.0)), "residual": residual, "final": final}

    def infer_sequence(self, mocap_seq: np.ndarray) -> Dict[str, float]:
        if self.model is None:
            return self._heuristic_sequence_score(mocap_seq)

        seq = self._resample_sequence(mocap_seq)
        arr = seq[None, ...].astype(np.float32)
        try:
            base, res, final = predict(self.model, arr)
            return {
                "base": float(base[0, 0]),
                "residual": float(res[0, 0]),
                "final": float(np.clip(final[0, 0], 0.0, 100.0)),
            }
        except Exception:
            return self._heuristic_sequence_score(mocap_seq)

    def score_mocap_sequence(self, mocap_seq: np.ndarray) -> Dict[str, object]:
        result = self.infer_sequence(mocap_seq)
        score = int(round(result["final"]))
        feedback = self.feedback_from_score(score)
        return {
            "score": score,
            "base": result["base"],
            "residual": result["residual"],
            "final": result["final"],
            "feedback": feedback,
        }

    def feedback_from_score(self, score: int) -> str:
        if score >= 92:
            return "动作爆点命中率很高，整体控制非常稳定。"
        if score >= 85:
            return "动作完成度优秀，节奏和线条都比较到位。"
        if score >= 75:
            return "整体已经成型，但细节稳定性还可以继续提升。"
        return random.choice(self.feedback_pool)

    def _score_buffer(self) -> Tuple[int, str]:
        if len(self.buffer) < 8:
            return self._mock()
        result = self.score_mocap_sequence(np.stack(list(self.buffer), axis=0))
        return int(result["score"]), str(result["feedback"])

    def _submit_frame(self, mocap_frame: np.ndarray) -> Optional[Tuple[int, str]]:
        now = time.time()
        self.buffer.append(np.asarray(mocap_frame, dtype=np.float32))
        if (now - self.last_t) < self.interval:
            return None
        self.last_t = now
        return self._score_buffer()

    def score_frame(self, frame_rgb: np.ndarray) -> Optional[Tuple[int, str]]:
        return self._submit_frame(self._frame_to_mocap_like(frame_rgb))

    def score_mocap_frame(self, mocap_frame: np.ndarray) -> Optional[Tuple[int, str]]:
        return self._submit_frame(mocap_frame)

