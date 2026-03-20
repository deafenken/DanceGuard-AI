import os
import random
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np

from .bvh_io import load_bvh_as_mocap
from .infer import load_model, predict


STANDARD_REFERENCE_PATHS = {
    "黑走马 (Kara Jorga)": [
        "Kara Jorga.bvh",
        os.path.join("assets", "data", "Kara Jorga.bvh"),
        os.path.join("assets", "standard", "kara-jorga.bvh"),
    ],
    "木卡姆 (Muqam)": [
        "Muqam.bvh",
        os.path.join("assets", "data", "Muqam.bvh"),
        os.path.join("assets", "standard", "muqam.bvh"),
    ],
}

JOINT_NAMES = [
    "Hips", "Spine", "Chest", "Neck", "Head", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
    "LeftToes", "RightUpperLeg", "RightLowerLeg", "RightFoot", "RightToes", "LeftShoulder",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightShoulder", "RightUpperArm",
    "RightLowerArm", "RightHand", "Spine", "Chest", "Neck",
]

KEY_JOINTS = [0, 4, 7, 11, 13, 16, 17, 20]
ROOT_IDX = 0
HEAD_IDX = 4
LEFT_FOOT_IDX = 7
RIGHT_FOOT_IDX = 11
LEFT_SHOULDER_IDX = 13
RIGHT_SHOULDER_IDX = 17
LEFT_HAND_IDX = 16
RIGHT_HAND_IDX = 20
LEFT_HIP_IDX = 5
RIGHT_HIP_IDX = 9


class Scorer:
    """实时与离线共用的评分器。优先依据标准动作相似度评分，模型仅提供小残差修正。"""

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
        self.reference_path = self._resolve_reference_path(dance_type)
        self.reference_raw = self._load_reference_sequence(self.reference_path)
        self.reference_seq = self._prepare_reference(self.reference_raw) if self.reference_raw is not None else None
        self.last_analysis: Dict[str, object] = {
            "base": 72.0,
            "residual": 0.0,
            "final": 72.0,
            "distance": 0.0,
            "worst_joint": "Hips",
            "joint_errors": [],
            "has_reference": self.reference_seq is not None,
        }

        self.model = None
        if os.path.exists(ckpt_path):
            try:
                self.model = load_model(ckpt_path, joints=joints)
            except Exception as exc:
                print(f"[WARN] 模型加载失败，将退回标准动作评分: {exc}")
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

    def _resolve_reference_path(self, dance_type: str) -> str:
        for candidate in STANDARD_REFERENCE_PATHS.get(dance_type, []):
            if os.path.exists(candidate):
                return candidate
        return ""

    def _load_reference_sequence(self, path: str) -> Optional[np.ndarray]:
        if not path:
            return None
        try:
            return load_bvh_as_mocap(path, joints=self.joints).astype(np.float32)
        except Exception as exc:
            print(f"[WARN] 标准动作加载失败 {path}: {exc}")
            return None

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

    def _resample_sequence(self, mocap_seq: np.ndarray, target_len: Optional[int] = None) -> np.ndarray:
        seq = self._normalize_sequence_shape(mocap_seq)
        target = target_len or self.seq_len
        if len(seq) == target:
            return seq
        if len(seq) == 0:
            return np.zeros((target, self.joints, 3), dtype=np.float32)
        idx = np.linspace(0, len(seq) - 1, target)
        base = np.arange(len(seq), dtype=np.float32)
        out = np.empty((target, self.joints, 3), dtype=np.float32)
        for joint in range(self.joints):
            for axis in range(3):
                out[:, joint, axis] = np.interp(idx, base, seq[:, joint, axis])
        return out

    def _safe_norm(self, vec: np.ndarray, axis: int = -1, keepdims: bool = False) -> np.ndarray:
        return np.linalg.norm(vec, axis=axis, keepdims=keepdims) + 1e-6

    def _rotation_y(self, angles: np.ndarray) -> np.ndarray:
        c = np.cos(angles)
        s = np.sin(angles)
        rot = np.zeros((len(angles), 3, 3), dtype=np.float32)
        rot[:, 0, 0] = c
        rot[:, 0, 2] = s
        rot[:, 1, 1] = 1.0
        rot[:, 2, 0] = -s
        rot[:, 2, 2] = c
        return rot

    def _normalize_pose_sequence(self, mocap_seq: np.ndarray) -> np.ndarray:
        seq = self._normalize_sequence_shape(mocap_seq).copy()
        if len(seq) == 0:
            return seq
        root = seq[:, ROOT_IDX:ROOT_IDX + 1, :].copy()
        seq -= root

        left_anchor = 0.5 * (seq[:, LEFT_SHOULDER_IDX, :] + seq[:, LEFT_HIP_IDX, :])
        right_anchor = 0.5 * (seq[:, RIGHT_SHOULDER_IDX, :] + seq[:, RIGHT_HIP_IDX, :])
        across = left_anchor - right_anchor
        across[:, 1] = 0.0
        across = across / self._safe_norm(across, keepdims=True)

        up = np.zeros_like(across)
        up[:, 1] = 1.0
        forward = np.cross(up, across)
        forward = forward / self._safe_norm(forward, keepdims=True)
        yaw = np.arctan2(forward[:, 0], forward[:, 2]).astype(np.float32)
        rot = self._rotation_y(-yaw)
        seq = np.einsum("tij,tkj->tki", rot, seq)

        body_scale = (
            np.linalg.norm(seq[:, HEAD_IDX, :], axis=1)
            + np.linalg.norm(seq[:, LEFT_FOOT_IDX, :], axis=1)
            + np.linalg.norm(seq[:, RIGHT_FOOT_IDX, :], axis=1)
            + 0.5 * np.linalg.norm(seq[:, LEFT_HAND_IDX, :] - seq[:, RIGHT_HAND_IDX, :], axis=1)
        ) / 3.5
        scale = np.maximum(np.median(body_scale), 1e-3).astype(np.float32)
        seq /= scale
        return seq.astype(np.float32)

    def _prepare_reference(self, mocap_seq: np.ndarray) -> np.ndarray:
        seq = self._normalize_pose_sequence(mocap_seq)
        target = min(max(len(seq), self.seq_len), 96)
        return self._resample_sequence(seq, target_len=target)

    def _dtw_path(self, seq_a: np.ndarray, seq_b: np.ndarray) -> Tuple[float, List[Tuple[int, int]]]:
        n, m = len(seq_a), len(seq_b)
        cost = np.full((n + 1, m + 1), np.inf, dtype=np.float32)
        cost[0, 0] = 0.0
        back = np.zeros((n, m, 2), dtype=np.int16)
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                d = float(np.linalg.norm(seq_a[i - 1] - seq_b[j - 1]))
                candidates = (cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
                arg = int(np.argmin(candidates))
                if arg == 0:
                    prev = (i - 1, j)
                elif arg == 1:
                    prev = (i, j - 1)
                else:
                    prev = (i - 1, j - 1)
                cost[i, j] = d + candidates[arg]
                back[i - 1, j - 1] = (prev[0], prev[1])
        i, j = n, m
        path: List[Tuple[int, int]] = []
        while i > 0 and j > 0:
            path.append((i - 1, j - 1))
            i, j = back[i - 1, j - 1]
        path.reverse()
        return float(cost[n, m]), path

    def _joint_error_summary(self, seq_a: np.ndarray, seq_b: np.ndarray, path: List[Tuple[int, int]]) -> List[Dict[str, float]]:
        if not path:
            return []
        idx_a = np.asarray([p[0] for p in path], dtype=np.int32)
        idx_b = np.asarray([p[1] for p in path], dtype=np.int32)
        err = np.linalg.norm(seq_a[idx_a] - seq_b[idx_b], axis=-1)
        mean_err = err.mean(axis=0)
        summary = []
        for idx, val in enumerate(mean_err[: len(JOINT_NAMES)]):
            summary.append({"joint": JOINT_NAMES[idx], "error": float(val)})
        summary.sort(key=lambda x: x["error"], reverse=True)
        return summary

    def _reference_similarity(self, mocap_seq: np.ndarray) -> Dict[str, object]:
        if self.reference_seq is None:
            return {"base": 72.0, "distance": 0.22, "worst_joint": "Hips", "joint_errors": []}
        seq = self._normalize_pose_sequence(mocap_seq)
        target = min(max(len(seq), 24), 96)
        seq = self._resample_sequence(seq, target_len=target)
        ref = self._resample_sequence(self.reference_seq, target_len=target)
        feat_a = seq[:, KEY_JOINTS, :].reshape(target, -1)
        feat_b = ref[:, KEY_JOINTS, :].reshape(target, -1)
        total_dist, path = self._dtw_path(feat_a, feat_b)
        avg_dist = float(total_dist / max(len(path), 1))
        base = float(np.clip(100.0 * np.exp(-1.75 * avg_dist), 0.0, 100.0))
        joint_errors = self._joint_error_summary(seq, ref, path)
        worst_joint = joint_errors[0]["joint"] if joint_errors else "Hips"
        return {
            "base": base,
            "distance": avg_dist,
            "worst_joint": worst_joint,
            "joint_errors": joint_errors[:8],
        }

    def _model_residual(self, mocap_seq: np.ndarray, anchor_score: float) -> float:
        if self.model is None:
            return 0.0
        seq = self._normalize_pose_sequence(mocap_seq)
        seq = self._resample_sequence(seq, target_len=self.seq_len)
        arr = seq[None, ...].astype(np.float32)
        try:
            _, _, final = predict(self.model, arr)
            model_score = float(np.clip(final[0, 0], 0.0, 100.0))
            residual = float(np.clip((model_score - anchor_score) * 0.08, -2.0, 2.0))
            if anchor_score >= 95.0:
                residual = max(0.0, residual)
            return residual
        except Exception as exc:
            print(f"[WARN] 模型推理失败，忽略残差修正: {exc}")
            return 0.0

    def analyze_sequence(self, mocap_seq: np.ndarray) -> Dict[str, object]:
        seq = self._normalize_sequence_shape(mocap_seq)
        if len(seq) < 2:
            result = {"base": 72.0, "residual": 0.0, "final": 72.0, "distance": 0.22, "worst_joint": "Hips", "joint_errors": [], "has_reference": self.reference_seq is not None}
            self.last_analysis = result
            return result
        ref_result = self._reference_similarity(seq)
        residual = self._model_residual(seq, ref_result["base"])
        final = float(np.clip(float(ref_result["base"]) + residual, 0.0, 100.0))
        result = {
            "base": float(ref_result["base"]),
            "residual": residual,
            "final": final,
            "distance": float(ref_result["distance"]),
            "worst_joint": str(ref_result["worst_joint"]),
            "joint_errors": ref_result["joint_errors"],
            "has_reference": self.reference_seq is not None,
            "reference_path": self.reference_path,
        }
        self.last_analysis = result
        return result

    def infer_sequence(self, mocap_seq: np.ndarray) -> Dict[str, float]:
        result = self.analyze_sequence(mocap_seq)
        return {
            "base": float(result["base"]),
            "residual": float(result["residual"]),
            "final": float(result["final"]),
        }

    def score_mocap_sequence(self, mocap_seq: np.ndarray) -> Dict[str, object]:
        result = self.analyze_sequence(mocap_seq)
        score = int(round(float(result["final"])))
        feedback = self.feedback_from_score(score, str(result.get("worst_joint", "Hips")))
        return {
            "score": score,
            "base": result["base"],
            "residual": result["residual"],
            "final": result["final"],
            "distance": result["distance"],
            "worst_joint": result["worst_joint"],
            "joint_errors": result["joint_errors"],
            "feedback": feedback,
            "has_reference": result["has_reference"],
            "reference_path": result.get("reference_path", ""),
        }

    def feedback_from_score(self, score: int, worst_joint: str = "Hips") -> str:
        joint_hint = f"当前最需要修正的部位是 {worst_joint}。"
        if score >= 92:
            return f"动作爆点命中率很高，整体控制非常稳定。{joint_hint}"
        if score >= 85:
            return f"动作完成度优秀，节奏和线条都比较到位。{joint_hint}"
        if score >= 75:
            return f"整体已经成型，但细节稳定性还可以继续提升。{joint_hint}"
        return f"{random.choice(self.feedback_pool)} {joint_hint}"

    def _score_buffer(self) -> Tuple[int, str]:
        if len(self.buffer) < 4:
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


