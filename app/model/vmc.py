import os
import socket
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


JOINT_NAMES = [
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
    "LeftUpperArm",
    "LeftLowerArm",
    "RightLowerArm",
]

PARENTS = {
    "Hips": None,
    "Spine": "Hips",
    "Chest": "Spine",
    "Neck": "Chest",
    "Head": "Neck",
    "LeftUpperLeg": "Hips",
    "LeftLowerLeg": "LeftUpperLeg",
    "LeftFoot": "LeftLowerLeg",
    "LeftToes": "LeftFoot",
    "RightUpperLeg": "Hips",
    "RightLowerLeg": "RightUpperLeg",
    "RightFoot": "RightLowerLeg",
    "RightToes": "RightFoot",
    "LeftShoulder": "Chest",
    "LeftUpperArm": "LeftShoulder",
    "LeftLowerArm": "LeftUpperArm",
    "LeftHand": "LeftLowerArm",
    "RightShoulder": "Chest",
    "RightUpperArm": "RightShoulder",
    "RightLowerArm": "RightUpperArm",
    "RightHand": "RightLowerArm",
}

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


def _pad4(n: int) -> int:
    return (n + 3) & ~0x03


def _read_osc_string(payload: bytes, offset: int) -> Tuple[str, int]:
    end = payload.index(b"\x00", offset)
    raw = payload[offset:end]
    offset = _pad4(end + 1)
    return raw.decode("utf-8", errors="ignore"), offset


def _read_osc_args(payload: bytes, offset: int, tags: str):
    args = []
    for tag in tags:
        if tag == "s":
            value, offset = _read_osc_string(payload, offset)
        elif tag == "f":
            value = struct.unpack(">f", payload[offset : offset + 4])[0]
            offset += 4
        elif tag == "i":
            value = struct.unpack(">i", payload[offset : offset + 4])[0]
            offset += 4
        else:
            raise ValueError(f"Unsupported OSC tag: {tag}")
        args.append(value)
    return args, offset


def parse_osc_packet(payload: bytes):
    messages = []
    if payload.startswith(b"#bundle\x00"):
        offset = 16
        while offset + 4 <= len(payload):
            size = struct.unpack(">i", payload[offset : offset + 4])[0]
            offset += 4
            chunk = payload[offset : offset + size]
            offset += size
            messages.extend(parse_osc_packet(chunk))
        return messages

    address, offset = _read_osc_string(payload, 0)
    if not address:
        return messages
    tags, offset = _read_osc_string(payload, offset)
    if not tags.startswith(","):
        return messages
    args, _ = _read_osc_args(payload, offset, tags[1:])
    messages.append((address, args))
    return messages


def ensure_record_dir() -> str:
    path = os.path.join("assets", "data", "records")
    os.makedirs(path, exist_ok=True)
    return path


def export_simple_bvh(path: str, frames_xyz: np.ndarray, frame_time: float = 1 / 30.0):
    names = MODEL_JOINT_NAMES
    parents = [-1, 0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 2, 13, 14, 15, 2, 17, 18, 19, 1, 2, 3]
    first = frames_xyz[0]
    offsets = np.zeros_like(first)
    for idx, parent in enumerate(parents):
        offsets[idx] = first[idx] if parent == -1 else first[idx] - first[parent]

    children = {i: [] for i in range(len(names))}
    for idx, parent in enumerate(parents):
        if parent >= 0:
            children[parent].append(idx)

    lines: List[str] = ["HIERARCHY"]

    def emit_joint(idx: int, indent: int):
        prefix = "  " * indent
        joint_type = "ROOT" if parents[idx] == -1 else "JOINT"
        lines.append(f"{prefix}{joint_type} {names[idx]}")
        lines.append(f"{prefix}" + "{")
        off = offsets[idx]
        lines.append(f"{prefix}  OFFSET {off[0]:.6f} {off[1]:.6f} {off[2]:.6f}")
        if parents[idx] == -1:
            lines.append(f"{prefix}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")
        else:
            lines.append(f"{prefix}  CHANNELS 3 Zrotation Xrotation Yrotation")
        for child in children[idx]:
            emit_joint(child, indent + 1)
        if not children[idx]:
            lines.append(f"{prefix}  End Site")
            lines.append(f"{prefix}  " + "{")
            lines.append(f"{prefix}    OFFSET 0.0 0.0 0.0")
            lines.append(f"{prefix}  " + "}")
        lines.append(f"{prefix}" + "}")

    emit_joint(0, 0)
    lines.append("MOTION")
    lines.append(f"Frames: {frames_xyz.shape[0]}")
    lines.append(f"Frame Time: {frame_time:.8f}")
    for frame in frames_xyz:
        root = frame[0]
        channels = [root[0], root[1], root[2], 0.0, 0.0, 0.0]
        for _ in range(1, len(names)):
            channels.extend([0.0, 0.0, 0.0])
        lines.append(" ".join(f"{v:.6f}" for v in channels))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


@dataclass
class VmcFrame:
    timestamp: float
    joints: np.ndarray


class VmcReceiver:
    """最小可用的 VMC/OSC UDP 接收器，附带实时诊断指标。"""

    def __init__(self, host: str = "0.0.0.0", port: int = 39539):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        self.root_pos = np.zeros(3, dtype=np.float32)
        self.local_bones: Dict[str, np.ndarray] = {}
        self.last_frame_time = 0.0
        self.started_at = 0.0
        self.packet_count = 0
        self.frame_count = 0
        self.last_packet_time = 0.0
        self.frame_times = deque(maxlen=120)

    def start(self):
        if self.running:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(0.2)
        self.running = True
        self.started_at = time.time()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.sock:
            self.sock.close()
            self.sock = None

    def _loop(self):
        while self.running and self.sock:
            try:
                payload, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                messages = parse_osc_packet(payload)
            except Exception:
                continue

            with self.lock:
                self.packet_count += 1
                self.last_packet_time = time.time()
                for address, args in messages:
                    if address == "/VMC/Ext/Root/Pos" and len(args) >= 4:
                        self.root_pos = np.array([float(args[1]), float(args[2]), float(args[3])], dtype=np.float32)
                        self.last_frame_time = time.time()
                        self.frame_count += 1
                        self.frame_times.append(self.last_frame_time)
                    elif address == "/VMC/Ext/Bone/Pos" and len(args) >= 4:
                        bone_name = str(args[0])
                        self.local_bones[bone_name] = np.array(
                            [float(args[1]), float(args[2]), float(args[3])], dtype=np.float32
                        )
                        self.last_frame_time = time.time()

    def get_latest_frame(self) -> Optional[VmcFrame]:
        with self.lock:
            if not self.local_bones and not np.any(self.root_pos):
                return None
            bones = dict(self.local_bones)
            root = self.root_pos.copy()
            ts = self.last_frame_time

        absolute: Dict[str, np.ndarray] = {"Hips": root + bones.get("Hips", np.zeros(3, dtype=np.float32))}

        def resolve(name: str) -> np.ndarray:
            if name in absolute:
                return absolute[name]
            parent = PARENTS.get(name)
            local = bones.get(name, np.zeros(3, dtype=np.float32))
            absolute[name] = local if parent is None else resolve(parent) + local
            return absolute[name]

        for name in set(PARENTS):
            resolve(name)

        frame = np.zeros((len(MODEL_JOINT_NAMES), 3), dtype=np.float32)
        for idx, name in enumerate(MODEL_JOINT_NAMES):
            frame[idx] = absolute.get(name, np.zeros(3, dtype=np.float32))
        return VmcFrame(timestamp=ts, joints=frame)

    def metrics(self) -> Dict[str, float]:
        with self.lock:
            now = time.time()
            connected = self.last_packet_time > 0 and (now - self.last_packet_time) < 1.5
            fps = 0.0
            if len(self.frame_times) >= 2:
                duration = self.frame_times[-1] - self.frame_times[0]
                if duration > 0:
                    fps = (len(self.frame_times) - 1) / duration
            return {
                "connected": connected,
                "packet_count": self.packet_count,
                "frame_count": self.frame_count,
                "bone_count": len(self.local_bones),
                "fps": round(fps, 2),
                "last_packet_age": round(now - self.last_packet_time, 3) if self.last_packet_time else -1.0,
                "uptime_sec": round(now - self.started_at, 1) if self.started_at else 0.0,
            }


class MocapRecorder:
    def __init__(self, dance_name: str = "dance"):
        self.frames: List[np.ndarray] = []
        self.started_at = time.strftime("%Y%m%d_%H%M%S")
        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in dance_name).strip("_")
        self.dance_name = slug or "dance"

    def append(self, joints: np.ndarray):
        self.frames.append(joints.astype(np.float32).copy())

    def save(self) -> Tuple[str, str]:
        record_dir = ensure_record_dir()
        stem = f"{self.dance_name}_{self.started_at}"
        npy_path = os.path.join(record_dir, f"{stem}.npy")
        bvh_path = os.path.join(record_dir, f"{stem}.bvh")
        arr = np.stack(self.frames, axis=0) if self.frames else np.zeros((0, 24, 3), dtype=np.float32)
        np.save(npy_path, arr)
        if len(arr) > 0:
            export_simple_bvh(bvh_path, arr)
        else:
            with open(bvh_path, "w", encoding="utf-8") as f:
                f.write("")
        return npy_path, bvh_path
