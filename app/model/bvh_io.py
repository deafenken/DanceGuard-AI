import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


MODEL_JOINT_NAMES = [
    "Hips",
    "Spine",
    "Chest",
    "Neck",
    "Head",
    "LeftUpperLeg",
    "LeftLowerLeg",
    "LeftFoot",
    "LeftToes",
    "RightUpperLeg",
    "RightLowerLeg",
    "RightFoot",
    "RightToes",
    "LeftShoulder",
    "LeftUpperArm",
    "LeftLowerArm",
    "LeftHand",
    "RightShoulder",
    "RightUpperArm",
    "RightLowerArm",
    "RightHand",
    "Spine",
    "Chest",
    "Neck",
]

JOINT_ALIASES = {
    "Hips": ["Hips", "Hip", "Pelvis", "Root"],
    "Spine": ["Spine", "Spine1", "Spine01", "LowerSpine"],
    "Chest": ["Chest", "Spine2", "Spine02", "UpperSpine"],
    "Neck": ["Neck", "Neck1"],
    "Head": ["Head"],
    "LeftUpperLeg": ["LeftUpperLeg", "LeftUpLeg", "L_Thigh"],
    "LeftLowerLeg": ["LeftLowerLeg", "LeftLeg", "L_Calf"],
    "LeftFoot": ["LeftFoot", "L_Foot"],
    "LeftToes": ["LeftToeBase", "LeftToes", "L_Toe"],
    "RightUpperLeg": ["RightUpperLeg", "RightUpLeg", "R_Thigh"],
    "RightLowerLeg": ["RightLowerLeg", "RightLeg", "R_Calf"],
    "RightFoot": ["RightFoot", "R_Foot"],
    "RightToes": ["RightToeBase", "RightToes", "R_Toe"],
    "LeftShoulder": ["LeftShoulder", "L_Clavicle"],
    "LeftUpperArm": ["LeftUpperArm", "LeftArm", "L_UpperArm"],
    "LeftLowerArm": ["LeftLowerArm", "LeftForeArm", "L_ForeArm"],
    "LeftHand": ["LeftHand", "L_Hand"],
    "RightShoulder": ["RightShoulder", "R_Clavicle"],
    "RightUpperArm": ["RightUpperArm", "RightArm", "R_UpperArm"],
    "RightLowerArm": ["RightLowerArm", "RightForeArm", "R_ForeArm"],
    "RightHand": ["RightHand", "R_Hand"],
}


@dataclass
class JointNode:
    name: str
    parent: Optional[int]
    offset: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    channels: List[str] = field(default_factory=list)
    channel_indices: List[int] = field(default_factory=list)
    children: List[int] = field(default_factory=list)


def _rot_x(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float32)


def _rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)


def _rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)


def _channel_rotation(channels: List[str], values: List[float]) -> np.ndarray:
    rot = np.eye(3, dtype=np.float32)
    for channel, value in zip(channels, values):
        angle = math.radians(float(value))
        ch = channel.lower()
        if ch.startswith("xrotation"):
            rot = rot @ _rot_x(angle)
        elif ch.startswith("yrotation"):
            rot = rot @ _rot_y(angle)
        elif ch.startswith("zrotation"):
            rot = rot @ _rot_z(angle)
    return rot


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())

def _resolve_joint_map(names: List[str]) -> List[Optional[int]]:
    normalized = [(_normalize_name(name), idx) for idx, name in enumerate(names)]
    exact = {name: idx for name, idx in normalized}
    resolved: List[Optional[int]] = []
    for target in MODEL_JOINT_NAMES:
        idx = None
        aliases = [_normalize_name(alias) for alias in JOINT_ALIASES.get(target, [target])]
        for key in aliases:
            if key in exact:
                idx = exact[key]
                break
        if idx is None:
            for norm_name, norm_idx in normalized:
                if any(norm_name.endswith(key) for key in aliases):
                    idx = norm_idx
                    break
        resolved.append(idx)
    return resolved

def load_bvh_as_mocap(path: str, joints: int = 24) -> np.ndarray:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    try:
        motion_idx = raw_lines.index("MOTION")
    except ValueError as exc:
        raise ValueError("无效 BVH：缺少 MOTION 段") from exc

    hierarchy = raw_lines[:motion_idx]
    motion_lines = raw_lines[motion_idx + 1 :]

    nodes: List[JointNode] = []
    stack: List[int] = []
    channel_cursor = 0
    i = 0
    while i < len(hierarchy):
        line = hierarchy[i]
        if line.startswith(("ROOT ", "JOINT ")):
            name = line.split(maxsplit=1)[1]
            parent = stack[-1] if stack else None
            node = JointNode(name=name, parent=parent)
            nodes.append(node)
            idx = len(nodes) - 1
            if parent is not None:
                nodes[parent].children.append(idx)
            stack.append(idx)
            i += 1
            continue
        if line == "End Site":
            i += 4
            continue
        if line == "{":
            i += 1
            continue
        if line == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if line.startswith("OFFSET") and stack:
            vals = [float(v) for v in line.split()[1:4]]
            nodes[stack[-1]].offset = np.asarray(vals, dtype=np.float32)
            i += 1
            continue
        if line.startswith("CHANNELS") and stack:
            parts = line.split()
            count = int(parts[1])
            channels = parts[2 : 2 + count]
            node = nodes[stack[-1]]
            node.channels = channels
            node.channel_indices = list(range(channel_cursor, channel_cursor + count))
            channel_cursor += count
            i += 1
            continue
        i += 1

    frames_line = next((line for line in motion_lines if line.lower().startswith("frames:")), None)
    if not frames_line:
        raise ValueError("无效 BVH：缺少 Frames 信息")
    frame_count = int(frames_line.split(":", 1)[1].strip())
    numeric_lines = [line for line in motion_lines if line and not line.lower().startswith("frames:") and not line.lower().startswith("frame time:")]
    if len(numeric_lines) < frame_count:
        raise ValueError("无效 BVH：帧数据不足")

    motion = np.asarray([[float(x) for x in line.split()] for line in numeric_lines[:frame_count]], dtype=np.float32)
    if motion.shape[1] < channel_cursor:
        raise ValueError("无效 BVH：通道数量与帧数据不匹配")

    global_pos = np.zeros((frame_count, len(nodes), 3), dtype=np.float32)
    global_rot = np.zeros((frame_count, len(nodes), 3, 3), dtype=np.float32)

    for f in range(frame_count):
        row = motion[f]
        for idx, node in enumerate(nodes):
            trans = node.offset.astype(np.float32).copy()
            rot_channels = []
            rot_values = []
            for ch_name, ch_idx in zip(node.channels, node.channel_indices):
                low = ch_name.lower()
                value = row[ch_idx]
                if low == "xposition":
                    trans[0] = value
                elif low == "yposition":
                    trans[1] = value
                elif low == "zposition":
                    trans[2] = value
                else:
                    rot_channels.append(ch_name)
                    rot_values.append(value)
            local_rot = _channel_rotation(rot_channels, rot_values)
            if node.parent is None:
                global_rot[f, idx] = local_rot
                global_pos[f, idx] = trans
            else:
                parent = node.parent
                global_rot[f, idx] = global_rot[f, parent] @ local_rot
                global_pos[f, idx] = global_pos[f, parent] + global_rot[f, parent] @ trans

    mapping = _resolve_joint_map([node.name for node in nodes])
    out = np.zeros((frame_count, joints, 3), dtype=np.float32)
    for target_idx in range(min(joints, len(mapping))):
        src_idx = mapping[target_idx]
        if src_idx is not None:
            out[:, target_idx] = global_pos[:, src_idx]
    return out


