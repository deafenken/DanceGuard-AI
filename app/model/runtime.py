import os
import random
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .bvh_io import load_bvh_as_mocap
from .infer import load_model, predict


DANCE_KARA = "\u9ed1\u8d70\u9a6c (Kara Jorga)"
DANCE_MUQAM = "\u6728\u5361\u59c6 (Muqam)"

STANDARD_REFERENCE_PATHS = {
    DANCE_KARA: [
        "Kara Jorga.bvh",
        os.path.join("assets", "data", "Kara Jorga.bvh"),
        os.path.join("assets", "standard", "kara-jorga.bvh"),
    ],
    DANCE_MUQAM: [
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
CHEST_IDX = 2
NECK_IDX = 3
HEAD_IDX = 4
LEFT_HIP_IDX = 5
LEFT_KNEE_IDX = 6
LEFT_FOOT_IDX = 7
RIGHT_HIP_IDX = 9
RIGHT_KNEE_IDX = 10
RIGHT_FOOT_IDX = 11
LEFT_SHOULDER_IDX = 13
LEFT_UPPER_ARM_IDX = 14
LEFT_LOWER_ARM_IDX = 15
LEFT_HAND_IDX = 16
RIGHT_SHOULDER_IDX = 17
RIGHT_UPPER_ARM_IDX = 18
RIGHT_LOWER_ARM_IDX = 19
RIGHT_HAND_IDX = 20

ANGLE_TRIPLETS = [
    ("Neck", (CHEST_IDX, NECK_IDX, HEAD_IDX)),
    ("LeftShoulder", (CHEST_IDX, LEFT_SHOULDER_IDX, LEFT_UPPER_ARM_IDX)),
    ("LeftElbow", (LEFT_SHOULDER_IDX, LEFT_UPPER_ARM_IDX, LEFT_LOWER_ARM_IDX)),
    ("RightShoulder", (CHEST_IDX, RIGHT_SHOULDER_IDX, RIGHT_UPPER_ARM_IDX)),
    ("RightElbow", (RIGHT_SHOULDER_IDX, RIGHT_UPPER_ARM_IDX, RIGHT_LOWER_ARM_IDX)),
    ("LeftHip", (ROOT_IDX, LEFT_HIP_IDX, LEFT_KNEE_IDX)),
    ("LeftKnee", (LEFT_HIP_IDX, LEFT_KNEE_IDX, LEFT_FOOT_IDX)),
    ("RightHip", (ROOT_IDX, RIGHT_HIP_IDX, RIGHT_KNEE_IDX)),
    ("RightKnee", (RIGHT_HIP_IDX, RIGHT_KNEE_IDX, RIGHT_FOOT_IDX)),
]

CFPI_COMPONENT_WEIGHTS = {
    "joint_angle": 15.0,
    "trajectory": 15.0,
    "cultural": 10.0,
    "beat": 15.0,
    "accent": 10.0,
    "smoothness": 10.0,
    "stability": 10.0,
    "extension": 8.0,
    "expression": 7.0,
}

CFPI_DIMENSIONS = {
    "accuracy": ("joint_angle", "trajectory", "cultural"),
    "rhythm": ("beat", "accent"),
    "fluency": ("smoothness", "stability"),
    "expression": ("extension", "expression"),
}

CULTURAL_FEATURE_WEIGHTS = {
    "neck_shift": 1.5,
    "wrist_flip": 1.4,
    "shoulder_shimmy": 1.4,
    "hat_hold": 1.3,
}


class Scorer:
    """Runtime scorer using CFPI as the primary score and the model as a small residual."""

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
        self.last_analysis: Dict[str, Any] = self._default_analysis()
        self.last_analysis["has_reference"] = self.reference_seq is not None

        self.model = None
        if os.path.exists(ckpt_path):
            try:
                self.model = load_model(ckpt_path, joints=joints)
            except Exception as exc:
                print(f"[WARN] model load failed, fallback to CFPI main scoring: {exc}")
                self.model = None

        self.feedback_pool = [
            "\u624b\u81c2\u7ebf\u6761\u5f88\u597d\uff0c\u7ee7\u7eed\u4fdd\u6301\u3002",
            "\u6ce8\u610f\u9acb\u90e8\u5e26\u52a8\u548c\u91cd\u5fc3\u8f6c\u79fb\u3002",
            "\u8282\u594f\u5f88\u7a33\uff0c\u52a8\u4f5c\u8854\u63a5\u987a\u7545\u3002",
            "\u4e0a\u80a2\u5e45\u5ea6\u53ef\u4ee5\u518d\u6253\u5f00\u4e00\u4e9b\u3002",
            "\u811a\u6b65\u843d\u70b9\u7565\u6709\u504f\u79fb\uff0c\u6ce8\u610f\u7ad9\u4f4d\u3002",
            "\u52a8\u4f5c\u5b8c\u6210\u5ea6\u4e0d\u9519\uff0c\u4fdd\u6301\u7a33\u5b9a\u8f93\u51fa\u3002",
        ]

    def _default_analysis(self) -> Dict[str, Any]:
        components = {key: 72.0 for key in CFPI_COMPONENT_WEIGHTS}
        dimensions = {key: 72.0 for key in CFPI_DIMENSIONS}
        cultural = {key: 72.0 for key in CULTURAL_FEATURE_WEIGHTS}
        return {
            "base": 72.0,
            "residual": 0.0,
            "final": 72.0,
            "distance": 0.22,
            "worst_joint": "Hips",
            "joint_errors": [],
            "cfpi": {
                "total": 72.0,
                "dimensions": dimensions,
                "components": components,
                "cultural_features": cultural,
            },
            "has_reference": False,
            "reference_path": self.reference_path,
        }

    def _frame_to_mocap_like(self, frame_rgb: np.ndarray) -> np.ndarray:
        small = frame_rgb[::16, ::16, :]
        mean_rgb = np.mean(small, axis=(0, 1), dtype=np.float32)
        std_rgb = np.std(small, axis=(0, 1), dtype=np.float32)
        seed = np.concatenate([mean_rgb, std_rgb]).astype(np.float32)
        feat = np.resize(seed, self.joints * 3).astype(np.float32)
        return feat.reshape(self.joints, 3)

    def _mock(self) -> Tuple[int, str]:
        if self.dance_type == DANCE_KARA:
            score = int(max(70, min(98, random.gauss(90, 4))))
        else:
            score = int(max(55, min(97, random.gauss(80, 11))))
        return score, random.choice(self.feedback_pool)

    def _resolve_reference_path(self, dance_type: str) -> str:
        low = dance_type.lower()
        targets = []
        if "kara" in low or "jorga" in low or "\u9ed1\u8d70\u9a6c" in dance_type:
            targets.append(DANCE_KARA)
        if "muqam" in low or "\u6728\u5361\u59c6" in dance_type:
            targets.append(DANCE_MUQAM)
        if not targets:
            targets = list(STANDARD_REFERENCE_PATHS.keys())
        for target in targets:
            for candidate in STANDARD_REFERENCE_PATHS.get(target, []):
                if os.path.exists(candidate):
                    return candidate
        for candidates in STANDARD_REFERENCE_PATHS.values():
            for candidate in candidates:
                if os.path.exists(candidate):
                    return candidate
        return ""

    def _load_reference_sequence(self, path: str) -> Optional[np.ndarray]:
        if not path:
            return None
        try:
            return load_bvh_as_mocap(path, joints=self.joints).astype(np.float32)
        except Exception as exc:
            print(f"[WARN] reference motion load failed {path}: {exc}")
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

    def _angle_series(self, seq: np.ndarray, triplet: Tuple[int, int, int]) -> np.ndarray:
        a, b, c = triplet
        ba = seq[:, a] - seq[:, b]
        bc = seq[:, c] - seq[:, b]
        ba = ba / self._safe_norm(ba, keepdims=True)
        bc = bc / self._safe_norm(bc, keepdims=True)
        cosine = np.sum(ba * bc, axis=-1)
        cosine = np.clip(cosine, -1.0, 1.0)
        return np.arccos(cosine)

    def _safe_corr(self, a: np.ndarray, b: np.ndarray) -> float:
        if len(a) < 2 or len(b) < 2:
            return 1.0
        a = np.asarray(a, dtype=np.float32).reshape(-1)
        b = np.asarray(b, dtype=np.float32).reshape(-1)
        sa = float(np.std(a))
        sb = float(np.std(b))
        if sa < 1e-6 and sb < 1e-6:
            return 1.0
        if sa < 1e-6 or sb < 1e-6:
            return 0.0
        corr = np.corrcoef(a, b)[0, 1]
        if np.isnan(corr):
            return 0.0
        return float(np.clip((corr + 1.0) * 0.5, 0.0, 1.0))

    def _amplitude_ratio(self, a: np.ndarray, b: np.ndarray) -> float:
        aa = float(np.std(a)) + 1e-6
        bb = float(np.std(b)) + 1e-6
        return float(min(aa, bb) / max(aa, bb))

    def _shape_score(self, a: np.ndarray, b: np.ndarray) -> float:
        scale = float(np.std(b) + 0.25 * np.mean(np.abs(b)) + 1e-6)
        mae = float(np.mean(np.abs(a - b)))
        return float(np.exp(-mae / scale))

    def _series_similarity_score(self, a: np.ndarray, b: np.ndarray) -> float:
        corr = self._safe_corr(a, b)
        amp = self._amplitude_ratio(a, b)
        shape = self._shape_score(a, b)
        return float(np.clip(100.0 * (0.5 * corr + 0.25 * amp + 0.25 * shape), 0.0, 100.0))

    def _peak_positions(self, series: np.ndarray, topk: int = 8) -> np.ndarray:
        s = np.asarray(series, dtype=np.float32).reshape(-1)
        if len(s) == 0:
            return np.zeros((0,), dtype=np.int32)
        if len(s) < 3:
            return np.asarray([int(np.argmax(s))], dtype=np.int32)
        kernel = np.asarray([0.25, 0.5, 0.25], dtype=np.float32)
        smooth = np.convolve(s, kernel, mode="same")
        threshold = float(np.mean(smooth) + 0.25 * np.std(smooth))
        peaks: List[int] = []
        for idx in range(1, len(smooth) - 1):
            if smooth[idx] >= smooth[idx - 1] and smooth[idx] >= smooth[idx + 1] and smooth[idx] >= threshold:
                peaks.append(idx)
        if not peaks:
            peaks = [int(np.argmax(smooth))]
        peaks = sorted(peaks, key=lambda idx: smooth[idx], reverse=True)[:topk]
        peaks.sort()
        return np.asarray(peaks, dtype=np.int32)

    def _tempo_ratio(self, a_peaks: np.ndarray, b_peaks: np.ndarray) -> float:
        if len(a_peaks) < 2 or len(b_peaks) < 2:
            return 1.0
        a_int = np.diff(a_peaks).astype(np.float32)
        b_int = np.diff(b_peaks).astype(np.float32)
        a_med = float(np.median(a_int)) + 1e-6
        b_med = float(np.median(b_int)) + 1e-6
        return float(min(a_med, b_med) / max(a_med, b_med))

    def _accent_alignment_score(self, energy_a: np.ndarray, energy_b: np.ndarray) -> float:
        peaks_a = self._peak_positions(energy_a, topk=8)
        peaks_b = self._peak_positions(energy_b, topk=8)
        if len(peaks_a) == 0 or len(peaks_b) == 0:
            return 60.0
        length = max(len(energy_a), 1)
        align = []
        for peak in peaks_b:
            diff = float(np.min(np.abs(peaks_a - peak))) / length
            align.append(float(np.exp(-10.0 * diff)))
        count_ratio = float(min(len(peaks_a), len(peaks_b)) / max(len(peaks_a), len(peaks_b)))
        tempo_ratio = self._tempo_ratio(peaks_a, peaks_b)
        return float(np.clip(100.0 * (0.6 * np.mean(align) + 0.2 * count_ratio + 0.2 * tempo_ratio), 0.0, 100.0))

    def _beat_match_score(self, energy_a: np.ndarray, energy_b: np.ndarray) -> float:
        corr = self._safe_corr(energy_a, energy_b)
        peaks_a = self._peak_positions(energy_a, topk=10)
        peaks_b = self._peak_positions(energy_b, topk=10)
        tempo_ratio = self._tempo_ratio(peaks_a, peaks_b)
        envelope_ratio = self._amplitude_ratio(energy_a, energy_b)
        return float(np.clip(100.0 * (0.55 * corr + 0.25 * tempo_ratio + 0.20 * envelope_ratio), 0.0, 100.0))

    def _cultural_feature_scores(self, seq_a: np.ndarray, seq_b: np.ndarray) -> Dict[str, float]:
        neck_a = seq_a[:, HEAD_IDX, 0] - seq_a[:, CHEST_IDX, 0]
        neck_b = seq_b[:, HEAD_IDX, 0] - seq_b[:, CHEST_IDX, 0]

        left_wrist_a = seq_a[:, LEFT_HAND_IDX] - seq_a[:, LEFT_LOWER_ARM_IDX]
        left_wrist_b = seq_b[:, LEFT_HAND_IDX] - seq_b[:, LEFT_LOWER_ARM_IDX]
        right_wrist_a = seq_a[:, RIGHT_HAND_IDX] - seq_a[:, RIGHT_LOWER_ARM_IDX]
        right_wrist_b = seq_b[:, RIGHT_HAND_IDX] - seq_b[:, RIGHT_LOWER_ARM_IDX]
        wrist_a = np.concatenate([left_wrist_a[:, [0, 1]].reshape(-1), right_wrist_a[:, [0, 1]].reshape(-1)])
        wrist_b = np.concatenate([left_wrist_b[:, [0, 1]].reshape(-1), right_wrist_b[:, [0, 1]].reshape(-1)])

        shoulder_shimmy_a = seq_a[:, LEFT_SHOULDER_IDX, 1] - seq_a[:, RIGHT_SHOULDER_IDX, 1]
        shoulder_shimmy_b = seq_b[:, LEFT_SHOULDER_IDX, 1] - seq_b[:, RIGHT_SHOULDER_IDX, 1]

        hat_hold_a = np.minimum(
            np.linalg.norm(seq_a[:, LEFT_HAND_IDX] - seq_a[:, HEAD_IDX], axis=1),
            np.linalg.norm(seq_a[:, RIGHT_HAND_IDX] - seq_a[:, HEAD_IDX], axis=1),
        )
        hat_hold_b = np.minimum(
            np.linalg.norm(seq_b[:, LEFT_HAND_IDX] - seq_b[:, HEAD_IDX], axis=1),
            np.linalg.norm(seq_b[:, RIGHT_HAND_IDX] - seq_b[:, HEAD_IDX], axis=1),
        )
        hat_hold_a = np.exp(-2.0 * hat_hold_a)
        hat_hold_b = np.exp(-2.0 * hat_hold_b)

        return {
            "neck_shift": self._series_similarity_score(neck_a, neck_b),
            "wrist_flip": self._series_similarity_score(wrist_a, wrist_b),
            "shoulder_shimmy": self._series_similarity_score(shoulder_shimmy_a, shoulder_shimmy_b),
            "hat_hold": self._series_similarity_score(hat_hold_a, hat_hold_b),
        }

    def _cultural_completion_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> Tuple[float, Dict[str, float]]:
        feature_scores = self._cultural_feature_scores(seq_a, seq_b)
        total_weight = float(sum(CULTURAL_FEATURE_WEIGHTS.values()))
        weighted = sum(feature_scores[name] * weight for name, weight in CULTURAL_FEATURE_WEIGHTS.items())
        return float(weighted / total_weight), feature_scores

    def _extension_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> float:
        ext_a = np.stack([
            np.linalg.norm(seq_a[:, HEAD_IDX], axis=1),
            np.linalg.norm(seq_a[:, LEFT_HAND_IDX], axis=1),
            np.linalg.norm(seq_a[:, RIGHT_HAND_IDX], axis=1),
            np.linalg.norm(seq_a[:, LEFT_FOOT_IDX], axis=1),
            np.linalg.norm(seq_a[:, RIGHT_FOOT_IDX], axis=1),
        ], axis=1).mean(axis=1)
        ext_b = np.stack([
            np.linalg.norm(seq_b[:, HEAD_IDX], axis=1),
            np.linalg.norm(seq_b[:, LEFT_HAND_IDX], axis=1),
            np.linalg.norm(seq_b[:, RIGHT_HAND_IDX], axis=1),
            np.linalg.norm(seq_b[:, LEFT_FOOT_IDX], axis=1),
            np.linalg.norm(seq_b[:, RIGHT_FOOT_IDX], axis=1),
        ], axis=1).mean(axis=1)
        return self._series_similarity_score(ext_a, ext_b)

    def _expression_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> float:
        upper_speed_a = np.linalg.norm(np.diff(seq_a[:, [HEAD_IDX, LEFT_HAND_IDX, RIGHT_HAND_IDX, LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX]], axis=0), axis=-1).mean(axis=1)
        upper_speed_b = np.linalg.norm(np.diff(seq_b[:, [HEAD_IDX, LEFT_HAND_IDX, RIGHT_HAND_IDX, LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX]], axis=0), axis=-1).mean(axis=1)
        if len(upper_speed_a) < 2 or len(upper_speed_b) < 2:
            return 60.0
        accel_a = np.diff(upper_speed_a)
        accel_b = np.diff(upper_speed_b)
        speed_score = self._series_similarity_score(upper_speed_a, upper_speed_b)
        accel_score = self._series_similarity_score(accel_a, accel_b)
        return float(np.clip(0.55 * speed_score + 0.45 * accel_score, 0.0, 100.0))

    def _trajectory_score(self, avg_dist: float) -> float:
        return float(np.clip(100.0 * np.exp(-1.75 * avg_dist), 0.0, 100.0))

    def _joint_angle_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> float:
        diffs = []
        for _, triplet in ANGLE_TRIPLETS:
            angle_a = self._angle_series(seq_a, triplet)
            angle_b = self._angle_series(seq_b, triplet)
            diffs.append(float(np.mean(np.abs(angle_a - angle_b))))
        mean_diff = float(np.mean(diffs)) if diffs else 0.0
        return float(np.clip(100.0 * np.exp(-2.35 * mean_diff), 0.0, 100.0))

    def _smoothness_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> float:
        if len(seq_a) < 4 or len(seq_b) < 4:
            return 60.0
        jerk_a = np.linalg.norm(np.diff(seq_a, n=3, axis=0), axis=-1).mean(axis=1)
        jerk_b = np.linalg.norm(np.diff(seq_b, n=3, axis=0), axis=-1).mean(axis=1)
        return self._series_similarity_score(jerk_a, jerk_b)

    def _stability_score(self, seq_a: np.ndarray, seq_b: np.ndarray) -> float:
        speed_a = np.linalg.norm(np.diff(seq_a, axis=0), axis=-1).mean(axis=1)
        speed_b = np.linalg.norm(np.diff(seq_b, axis=0), axis=-1).mean(axis=1)
        cv_a = float(np.std(speed_a) / (np.mean(speed_a) + 1e-6))
        cv_b = float(np.std(speed_b) / (np.mean(speed_b) + 1e-6))
        ratio = float(np.exp(-abs(cv_a - cv_b) / (cv_b + 0.15)))
        corr = self._safe_corr(speed_a, speed_b)
        return float(np.clip(100.0 * (0.45 * ratio + 0.55 * corr), 0.0, 100.0))

    def _cfpi_breakdown(self, seq_a: np.ndarray, seq_b: np.ndarray, avg_dist: float) -> Dict[str, Any]:
        speed_a = np.linalg.norm(np.diff(seq_a, axis=0), axis=-1).mean(axis=1)
        speed_b = np.linalg.norm(np.diff(seq_b, axis=0), axis=-1).mean(axis=1)

        components = {
            "joint_angle": self._joint_angle_score(seq_a, seq_b),
            "trajectory": self._trajectory_score(avg_dist),
            "beat": self._beat_match_score(speed_a, speed_b),
            "accent": self._accent_alignment_score(speed_a, speed_b),
            "smoothness": self._smoothness_score(seq_a, seq_b),
            "stability": self._stability_score(seq_a, seq_b),
            "extension": self._extension_score(seq_a, seq_b),
            "expression": self._expression_score(seq_a, seq_b),
        }
        cultural_score, cultural_features = self._cultural_completion_score(seq_a, seq_b)
        components["cultural"] = cultural_score

        total = 0.0
        for key, weight in CFPI_COMPONENT_WEIGHTS.items():
            total += weight * float(components[key]) / 100.0

        dimensions = {}
        for name, keys in CFPI_DIMENSIONS.items():
            weight_sum = sum(CFPI_COMPONENT_WEIGHTS[key] for key in keys)
            dimensions[name] = round(sum(CFPI_COMPONENT_WEIGHTS[key] * float(components[key]) for key in keys) / weight_sum, 2)

        return {
            "total": round(float(np.clip(total, 0.0, 100.0)), 2),
            "dimensions": dimensions,
            "components": {key: round(float(value), 2) for key, value in components.items()},
            "cultural_features": {key: round(float(value), 2) for key, value in cultural_features.items()},
        }

    def _aligned_reference_metrics(self, mocap_seq: np.ndarray) -> Dict[str, Any]:
        if self.reference_seq is None:
            default = self._default_analysis()
            return {
                "base": default["base"],
                "distance": default["distance"],
                "worst_joint": default["worst_joint"],
                "joint_errors": default["joint_errors"],
                "cfpi": default["cfpi"],
            }

        seq = self._normalize_pose_sequence(mocap_seq)
        target = min(max(len(seq), 24), 96)
        seq = self._resample_sequence(seq, target_len=target)
        ref = self._resample_sequence(self.reference_seq, target_len=target)
        feat_a = seq[:, KEY_JOINTS, :].reshape(target, -1)
        feat_b = ref[:, KEY_JOINTS, :].reshape(target, -1)
        total_dist, path = self._dtw_path(feat_a, feat_b)
        avg_dist = float(total_dist / max(len(path), 1))
        if path:
            idx_a = np.asarray([p[0] for p in path], dtype=np.int32)
            idx_b = np.asarray([p[1] for p in path], dtype=np.int32)
            seq_aligned = seq[idx_a]
            ref_aligned = ref[idx_b]
        else:
            seq_aligned = seq
            ref_aligned = ref
        joint_errors = self._joint_error_summary(seq, ref, path)
        worst_joint = joint_errors[0]["joint"] if joint_errors else "Hips"
        cfpi = self._cfpi_breakdown(seq_aligned, ref_aligned, avg_dist)
        return {
            "base": float(cfpi["total"]),
            "distance": avg_dist,
            "worst_joint": worst_joint,
            "joint_errors": joint_errors[:8],
            "cfpi": cfpi,
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
            print(f"[WARN] model inference failed, ignore residual: {exc}")
            return 0.0

    def analyze_sequence(self, mocap_seq: np.ndarray) -> Dict[str, Any]:
        seq = self._normalize_sequence_shape(mocap_seq)
        if len(seq) < 2:
            result = self._default_analysis()
            result["has_reference"] = self.reference_seq is not None
            self.last_analysis = result
            return result
        ref_result = self._aligned_reference_metrics(seq)
        residual = self._model_residual(seq, ref_result["base"])
        final = float(np.clip(float(ref_result["base"]) + residual, 0.0, 100.0))
        result = {
            "base": float(ref_result["base"]),
            "residual": residual,
            "final": final,
            "distance": float(ref_result["distance"]),
            "worst_joint": str(ref_result["worst_joint"]),
            "joint_errors": ref_result["joint_errors"],
            "cfpi": ref_result["cfpi"],
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

    def score_mocap_sequence(self, mocap_seq: np.ndarray) -> Dict[str, Any]:
        result = self.analyze_sequence(mocap_seq)
        score = int(round(float(result["final"])))
        feedback = self.feedback_from_score(score, str(result.get("worst_joint", "Hips")), result.get("cfpi", {}))
        return {
            "score": score,
            "base": result["base"],
            "residual": result["residual"],
            "final": result["final"],
            "distance": result["distance"],
            "worst_joint": result["worst_joint"],
            "joint_errors": result["joint_errors"],
            "cfpi": result["cfpi"],
            "feedback": feedback,
            "has_reference": result["has_reference"],
            "reference_path": result.get("reference_path", ""),
        }

    def feedback_from_score(self, score: int, worst_joint: str = "Hips", cfpi: Optional[Dict[str, Any]] = None) -> str:
        joint_hint = f"\u5f53\u524d\u6700\u9700\u8981\u4fee\u6b63\u7684\u90e8\u4f4d\u662f {worst_joint}\u3002"
        if cfpi and cfpi.get("dimensions"):
            dim_name = min(cfpi["dimensions"], key=lambda key: cfpi["dimensions"][key])
            dim_map = {
                "accuracy": "\u52a8\u4f5c\u51c6\u786e\u5ea6",
                "rhythm": "\u8282\u594f\u540c\u6b65\u6027",
                "fluency": "\u6d41\u7545\u5ea6",
                "expression": "\u8868\u73b0\u529b",
            }
            dim_hint = f"\u5f53\u524d\u6700\u8584\u5f31\u7684\u8bc4\u5206\u7ef4\u5ea6\u662f {dim_map.get(dim_name, dim_name)}\u3002"
        else:
            dim_hint = ""
        if score >= 92:
            return f"\u52a8\u4f5c\u7206\u70b9\u547d\u4e2d\u7387\u5f88\u9ad8\uff0c\u6574\u4f53\u63a7\u5236\u975e\u5e38\u7a33\u5b9a\u3002{joint_hint}{dim_hint}"
        if score >= 85:
            return f"\u52a8\u4f5c\u5b8c\u6210\u5ea6\u4f18\u79c0\uff0c\u8282\u594f\u548c\u7ebf\u6761\u90fd\u6bd4\u8f83\u5230\u4f4d\u3002{joint_hint}{dim_hint}"
        if score >= 75:
            return f"\u6574\u4f53\u5df2\u7ecf\u6210\u578b\uff0c\u4f46\u7ec6\u8282\u7a33\u5b9a\u6027\u8fd8\u53ef\u4ee5\u7ee7\u7eed\u63d0\u5347\u3002{joint_hint}{dim_hint}"
        return f"{random.choice(self.feedback_pool)} {joint_hint}{dim_hint}"

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
