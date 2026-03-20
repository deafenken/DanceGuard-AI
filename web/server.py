import cgi
import json
import os
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import numpy as np

from app.model.runtime import Scorer
from app.model.vmc import MocapRecorder, VmcReceiver
from app.model.bvh_io import load_bvh_as_mocap
from app.store import GUEST_USER, STUDENT_ROLE, LocalStore

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
ASSETS_DIR = Path("assets")
IMPORTS_DIR = ASSETS_DIR / "imports"
WEIGHTS_DIR = ASSETS_DIR / "weights"

DANCE_MODELS = {
    "黑走马 (Kara Jorga)": {"code": "kara_jorga", "weight": str(WEIGHTS_DIR / "best_dance_scoring.ckpt"), "desc": "哈萨克族舞种，动作更强调稳定的马步与律动。"},
    "木卡姆 (Muqam)": {"code": "muqam", "weight": str(WEIGHTS_DIR / "best_dance_scoring.ckpt"), "desc": "维吾尔族舞种，动作更强调上肢曲线和节奏变化。"},
}

JOINT_NAMES = [
    "Hips", "Spine", "Chest", "Neck", "Head", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
    "LeftToes", "RightUpperLeg", "RightLowerLeg", "RightFoot", "RightToes", "LeftShoulder",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightShoulder", "RightUpperArm",
    "RightLowerArm", "RightHand", "Spine", "Chest", "Neck",
]


def _json(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8")) if raw else {}


def _read_form(handler: BaseHTTPRequestHandler):
    env = {"REQUEST_METHOD": "POST", "CONTENT_TYPE": handler.headers.get("Content-Type", ""), "CONTENT_LENGTH": handler.headers.get("Content-Length", "0")}
    return cgi.FieldStorage(fp=handler.rfile, headers=handler.headers, environ=env, keep_blank_values=True)


def _grade(score: float) -> str:
    if score >= 92:
        return "S"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    return "C"


def _query(parsed, key: str, default: str = "") -> str:
    return parse_qs(parsed.query).get(key, [default])[0]


def _asset_url(path: str) -> str:
    if not path:
        return ""
    norm = str(path).replace("\\", "/")
    return "/" + norm if norm.startswith("assets/") else ""


def _load_mocap_sequence(path: str) -> np.ndarray:
    lower = path.lower()
    if lower.endswith(".npy"):
        arr = np.load(path)
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim != 3 or arr.shape[-1] != 3:
            raise ValueError("仅支持 [T, J, 3] 或 [1, T, J, 3] 的 NPY 动作序列")
        return arr.astype(np.float32)
    if lower.endswith(".bvh"):
        return load_bvh_as_mocap(path)
    raise ValueError("当前仅支持 NPY 或 BVH 动作文件")


_ANALYSIS_SCORERS: Dict[str, Scorer] = {}


def _analysis_scorer(dance_type: str) -> Optional[Scorer]:
    if dance_type not in DANCE_MODELS:
        return None
    if dance_type not in _ANALYSIS_SCORERS:
        _ANALYSIS_SCORERS[dance_type] = Scorer(dance_type=dance_type, ckpt_path="")
    return _ANALYSIS_SCORERS[dance_type]


def _sequence_analysis(seq: np.ndarray, dance_type: str = "") -> Dict[str, Any]:
    if len(seq) < 2:
        return {"worst_joint": "Hips", "joint_scores": [{"joint": "Hips", "score": 0.0, "error": 0.0}], "segments": [{"index": 1, "start_sec": 0.0, "end_sec": 0.0, "energy": 0.0}]}
    scorer = _analysis_scorer(dance_type)
    result = scorer.analyze_sequence(seq) if scorer is not None else {"worst_joint": "Hips", "joint_errors": []}
    joint_errors = result.get("joint_errors", []) or []
    if joint_errors:
        max_err = max(max(float(item.get("error", 0.0)) for item in joint_errors), 1e-6)
        joint_scores = [
            {
                "joint": item["joint"],
                "score": round(max(0.0, 100.0 - float(item.get("error", 0.0)) / max_err * 100.0), 2),
                "error": round(float(item.get("error", 0.0)), 5),
            }
            for item in joint_errors[:8]
        ]
    else:
        velocity = np.linalg.norm(np.diff(seq, axis=0), axis=-1)
        energy = velocity.mean(axis=0)
        max_energy = float(np.max(energy)) if float(np.max(energy)) > 0 else 1.0
        joint_scores = []
        for idx in range(min(len(JOINT_NAMES), len(energy))):
            joint_scores.append({"joint": JOINT_NAMES[idx], "score": round(max(0.0, 100.0 - float(energy[idx] / max_energy * 100.0)), 2), "error": round(float(energy[idx]), 5)})
        joint_scores.sort(key=lambda x: (x["score"], -x["error"]))
    velocity = np.linalg.norm(np.diff(seq, axis=0), axis=-1)
    seg_len = max(1, len(velocity) // 4)
    segments = []
    for seg_idx in range(4):
        start = seg_idx * seg_len
        end = len(velocity) if seg_idx == 3 else min(len(velocity), (seg_idx + 1) * seg_len)
        if start >= len(velocity):
            break
        segments.append({"index": seg_idx + 1, "start_sec": round(start / 30.0, 2), "end_sec": round(end / 30.0, 2), "energy": round(float(np.mean(velocity[start:end])), 5)})
    return {"worst_joint": str(result.get("worst_joint", joint_scores[0]["joint"] if joint_scores else "Hips")), "joint_scores": joint_scores, "segments": segments}


def _sequence_report(seq: np.ndarray, score: int, dance_type: str, feedback: str) -> str:
    analysis = _sequence_analysis(seq, dance_type)
    if len(seq) < 2:
        return f"{dance_type} ???????????????? {score}?"
    velocity = np.linalg.norm(np.diff(seq, axis=0), axis=-1)
    return (
        f"{dance_type} ??????????? {score}?"
        f" ?????? {float(np.mean(velocity)):.3f}?????? {float(np.std(velocity)):.3f}?"
        f" ??????????? {analysis['worst_joint']}?"
        f" ?????{feedback}"
    )


class SessionManager:
    def __init__(self):
        self.store = LocalStore()
        self.feed = deque(maxlen=20)
        self.running = False
        self.receiver: Optional[VmcReceiver] = None
        self.recorder: Optional[MocapRecorder] = None
        self.scorer: Optional[Scorer] = None
        self.last_frame_ts = 0.0
        self.record_info: Dict[str, str] = {"npy": "", "bvh": ""}
        self.score_history = []
        self.state = {}
        self.thread = None
        self.reset_state()

    def reset_state(self):
        state = self.store.get_state()
        self.state = {"active": False, "dance_type": "未启动", "host": "0.0.0.0", "port": 39539, "score": 0, "feedback": "等待开始", "rank": "IDLE", "model_status": "未加载", "elapsed_sec": 0, "best_combo": 0, "combo": 0, "stats": {"PERFECT": 0, "GREAT": 0, "GOOD": 0, "WARN": 0}, "started_at": 0.0, "last_update": 0.0, "current_user": state.get("current_user", GUEST_USER), "current_role": state.get("current_role", STUDENT_ROLE), "last_import_path": state.get("last_import_path", ""), "weakest_joint": "--"}

    def _scope_username(self) -> Optional[str]:
        return self.store.history_scope(self.state["current_user"], self.state["current_role"])

    def _feed_item(self, rank: str, title: str, detail: str):
        return {"rank": rank, "title": title, "detail": detail, "time": time.strftime("%H:%M:%S")}

    def _judge(self, score: int):
        if score < 70:
            return "WARN", "动作偏差较大"
        if score < 85:
            return "GOOD", "节奏保持稳定"
        if score < 92:
            return "GREAT", "动作完成度优秀"
        return "PERFECT", "节奏爆点命中"

    def start(self, dance_type: str, host: str, port: int):
        if self.running:
            return {"ok": False, "message": "会话已在运行中"}
        self.reset_state()
        self.state.update({"active": True, "dance_type": dance_type, "host": host, "port": port, "started_at": time.time()})
        weight_path = DANCE_MODELS.get(dance_type, DANCE_MODELS["黑走马 (Kara Jorga)"])["weight"]
        self.receiver = VmcReceiver(host=host, port=port)
        self.recorder = MocapRecorder(dance_type)
        self.scorer = Scorer(dance_type=dance_type, ckpt_path=weight_path)
        self.state["model_status"] = "真实模型" if self.scorer.model is not None else "降级评分"
        self.running = True
        import threading
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.feed.appendleft(self._feed_item("SYSTEM", "会话启动", f"{dance_type} / {host}:{port}"))
        return {"ok": True, "message": f"正在加载 {dance_type} 的评分链路"}

    def stop(self):
        if not self.running:
            return {"ok": True, "message": "当前没有运行中的会话"}
        now = time.time()
        if self.state.get("started_at"):
            self.state["elapsed_sec"] = int(now - float(self.state["started_at"]))
        self.state["active"] = False
        self.state["last_update"] = now
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        return {"ok": True, "message": "评分会话已停止"}

    def _loop(self):
        try:
            assert self.receiver is not None
            self.receiver.start()
        except OSError as exc:
            self.feed.appendleft(self._feed_item("WARN", "VMC 监听失败", str(exc)))
            self.running = False
            self.state["active"] = False
            return
        while self.running:
            frame = self.receiver.get_latest_frame() if self.receiver else None
            now = time.time()
            if self.state["started_at"]:
                self.state["elapsed_sec"] = int(now - float(self.state["started_at"]))
            if frame and frame.timestamp > self.last_frame_ts:
                self.last_frame_ts = frame.timestamp
                if self.recorder:
                    self.recorder.append(frame.joints)
                result = self.scorer.score_mocap_frame(frame.joints) if self.scorer else None
                if self.recorder and len(self.recorder.frames) >= 8 and self.scorer:
                    try:
                        recent_seq = np.stack(self.recorder.frames[-32:], axis=0).astype(np.float32)
                        self.state["weakest_joint"] = str(self.scorer.analyze_sequence(recent_seq).get("worst_joint", "--"))
                    except Exception as exc:
                        print(f"[WARN] 实时最弱关节分析失败: {exc}")
                        self.state["weakest_joint"] = "--"
                if result is not None:
                    score, feedback = result
                    rank, title = self._judge(score)
                    self.state["score"] = score
                    self.state["feedback"] = feedback
                    self.state["rank"] = rank
                    self.state["last_update"] = now
                    self.score_history.append(score)
                    self.state["stats"][rank] += 1
                    self.state["combo"] = self.state["combo"] + 1 if score >= 90 else max(0, self.state["combo"] - 1) if score >= 78 else 0
                    self.state["best_combo"] = max(self.state["best_combo"], self.state["combo"])
                    self.feed.appendleft(self._feed_item(rank, title, feedback))
            time.sleep(0.02)
        self._finalize()
        self.receiver = None
        self.recorder = None
        self.scorer = None
        self.thread = None
        self.running = False

    def _finalize(self):
        if self.receiver:
            self.receiver.stop()
        npy_path, bvh_path = self.recorder.save() if self.recorder else ("", "")
        self.record_info = {"npy": npy_path, "bvh": bvh_path}
        avg_score = sum(self.score_history) / max(len(self.score_history), 1) if self.score_history else 0.0
        duration_sec = int(time.time() - float(self.state.get("started_at", 0.0))) if self.state.get("started_at") else 0
        if self.recorder and self.recorder.frames and self.scorer:
            try:
                final_seq = np.stack(self.recorder.frames, axis=0).astype(np.float32)
                self.state["weakest_joint"] = str(self.scorer.analyze_sequence(final_seq).get("worst_joint", "--"))
            except Exception as exc:
                print(f"[WARN] 会话结束最弱关节分析失败: {exc}")
                pass
        self.store.save_history({"username": self.state["current_user"], "role": self.state["current_role"], "dance_type": self.state["dance_type"], "avg_score": avg_score, "best_combo": self.state["best_combo"], "duration_sec": duration_sec, "grade": _grade(avg_score), "record_text": f"已保存录制：{npy_path} | {bvh_path}" if npy_path or bvh_path else "", "summary_report": f"本轮实时评估结束，平均分 {avg_score:.1f}，最高连击 {self.state['best_combo']}。", "summary_image": "", "npy_path": npy_path, "bvh_path": bvh_path, "source_type": "live_vmc", "source_path": npy_path or bvh_path})
        self.feed.appendleft(self._feed_item("SYSTEM", "会话结束", self.record_info["bvh"] or self.record_info["npy"] or "本轮评分已结束"))
        self.state["active"] = False
        self.state["elapsed_sec"] = duration_sec

    def snapshot(self):
        metrics = self.receiver.metrics() if self.receiver else {"connected": False, "packet_count": 0, "frame_count": 0, "bone_count": 0, "fps": 0.0, "last_packet_age": -1.0, "uptime_sec": 0.0}
        self.state["vmc_metrics"] = metrics
        self.state["last_import_path"] = self.store.get_state().get("last_import_path", "")
        return {"state": dict(self.state), "feed": list(self.feed), "record": dict(self.record_info)}

    def history(self, dance_type: str = "", grade: str = "", keyword: str = ""):
        rows = self.store.list_history(self._scope_username(), dance_type=dance_type, grade=grade, keyword=keyword)
        for row in rows:
            row["npy_url"] = _asset_url(row.get("npy_path", ""))
            row["bvh_url"] = _asset_url(row.get("bvh_path", ""))
            row["source_url"] = _asset_url(row.get("source_path", ""))
            row["summary_image_url"] = _asset_url(row.get("summary_image", ""))
        return rows


SESSION = SessionManager()


class WebHandler(BaseHTTPRequestHandler):
    def _serve_file(self, root: Path, relative: str):
        file_path = (root / relative).resolve()
        if not str(file_path).startswith(str(root.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime = "text/plain; charset=utf-8"
        if file_path.suffix == ".html": mime = "text/html; charset=utf-8"
        elif file_path.suffix == ".css": mime = "text/css; charset=utf-8"
        elif file_path.suffix == ".js": mime = "application/javascript; charset=utf-8"
        elif file_path.suffix in {".png", ".jpg", ".jpeg", ".webp"}: mime = f"image/{file_path.suffix[1:]}"
        elif file_path.suffix == ".wav": mime = "audio/wav"
        elif file_path.suffix == ".svg": mime = "image/svg+xml"
        elif file_path.suffix == ".mp4": mime = "video/mp4"
        elif file_path.suffix == ".webm": mime = "video/webm"
        elif file_path.suffix == ".mov": mime = "video/quicktime"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        if file_path.suffix in {".html", ".css", ".js"}:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _stream_events(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                self.wfile.write(f"event: state\ndata: {json.dumps(SESSION.snapshot(), ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.write(f"event: history\ndata: {json.dumps(SESSION.history(), ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.write(f"event: imports\ndata: {json.dumps(SESSION.store.list_imports(SESSION._scope_username()), ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def _handle_import_upload(self):
        form = _read_form(self)
        file_item = form["file"] if "file" in form else None
        dance_type = form.getvalue("dance_type", "黑走马 (Kara Jorga)")
        if file_item is None or not getattr(file_item, "filename", ""):
            return _json(self, {"ok": False, "message": "未收到上传文件"}, status=400)
        filename = os.path.basename(file_item.filename)
        ext = Path(filename).suffix.lower()
        IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stored_path = IMPORTS_DIR / f"{Path(filename).stem}_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        with open(stored_path, "wb") as f:
            f.write(file_item.file.read())
        state = SESSION.store.get_state()
        import_id = SESSION.store.save_import_record(state["current_user"], state["current_role"], filename, str(stored_path), ext, eval_status="已导入")
        SESSION.store.set_state(last_import_path=str(stored_path))
        if ext in {".npy", ".bvh"}:
            try:
                seq = _load_mocap_sequence(str(stored_path))
                scorer = Scorer(dance_type=dance_type, ckpt_path=DANCE_MODELS.get(dance_type, DANCE_MODELS["黑走马 (Kara Jorga)"])["weight"])
                result = scorer.score_mocap_sequence(seq)
                grade = _grade(float(result["final"]))
                report = _sequence_report(seq, int(result["score"]), dance_type, str(result["feedback"]))
                history_id = SESSION.store.save_history({"username": state["current_user"], "role": state["current_role"], "dance_type": dance_type, "avg_score": float(result["final"]), "best_combo": 0, "duration_sec": int(len(seq) / 30), "grade": grade, "record_text": f"离线导入评估：{stored_path}", "summary_report": report, "summary_image": "", "npy_path": str(stored_path) if ext == ".npy" else "", "bvh_path": str(stored_path) if ext == ".bvh" else "", "source_type": "offline_npy" if ext == ".npy" else "offline_bvh", "source_path": str(stored_path)})
                SESSION.store.update_import_result(import_id, "已评估", float(result["final"]), grade, history_id)
                return _json(self, {"ok": True, "message": f"{ext.upper().replace('.', '')} 动作序列已完成离线评估", "import_id": import_id, "history_id": history_id, "result": result, "report": report})
            except Exception as exc:
                SESSION.store.update_import_result(import_id, f"评估失败: {exc}")
                return _json(self, {"ok": False, "message": f"导入失败：{exc}"}, status=400)
        SESSION.store.update_import_result(import_id, "已归档，暂不支持自动评分")
        return _json(self, {"ok": True, "message": f"文件已归档到 {stored_path}，当前仅对 NPY/BVH 动作序列提供自动评分。", "import_id": import_id})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/": return self._serve_file(STATIC_DIR, "index.html")
        if parsed.path.startswith("/static/"): return self._serve_file(STATIC_DIR, parsed.path.replace("/static/", "", 1))
        if parsed.path.startswith("/assets/"): return self._serve_file(ASSETS_DIR, parsed.path.replace("/assets/", "", 1))
        if parsed.path == "/api/stream": return self._stream_events()
        if parsed.path == "/api/state": return _json(self, SESSION.snapshot())
        if parsed.path == "/api/history": return _json(self, {"items": SESSION.history(_query(parsed, "dance_type"), _query(parsed, "grade"), _query(parsed, "keyword"))})
        if parsed.path == "/api/history/get":
            history_id = int(_query(parsed, "id", "0") or 0)
            item = SESSION.store.get_history(history_id)
            if item:
                item["npy_url"] = _asset_url(item.get("npy_path", ""))
                item["bvh_url"] = _asset_url(item.get("bvh_path", ""))
                item["source_url"] = _asset_url(item.get("source_path", ""))
                item["summary_image_url"] = _asset_url(item.get("summary_image", ""))
                motion_path = item.get("npy_path") or item.get("bvh_path") or item.get("source_path")
                if motion_path and os.path.exists(motion_path) and str(motion_path).lower().endswith((".npy", ".bvh")):
                    try:
                        item["analysis"] = _sequence_analysis(_load_mocap_sequence(motion_path), item.get("dance_type", ""))
                    except Exception:
                        item["analysis"] = None
            return _json(self, {"item": item})
        if parsed.path == "/api/models": return _json(self, {"items": [{"name": name, "code": meta["code"], "desc": meta["desc"], "weight": meta["weight"], "exists": os.path.exists(meta["weight"])} for name, meta in DANCE_MODELS.items()]})
        if parsed.path == "/api/device":
            snap = SESSION.snapshot()["state"]
            return _json(self, {"vmc": snap.get("vmc_metrics", {}), "host": snap.get("host", "0.0.0.0"), "port": snap.get("port", 39539), "session_active": snap.get("active", False), "record_path": SESSION.record_info})
        if parsed.path == "/api/imports": return _json(self, {"items": SESSION.store.list_imports(SESSION._scope_username())})
        if parsed.path == "/api/user": return _json(self, {"state": SESSION.store.get_state(), "users": SESSION.store.list_users()})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/start":
            payload = _read_json(self)
            return _json(self, SESSION.start(payload.get("dance_type", "黑走马 (Kara Jorga)"), payload.get("host", "0.0.0.0"), int(payload.get("port", 39539))))
        if parsed.path == "/api/stop": return _json(self, SESSION.stop())
        if parsed.path == "/api/auth/login":
            payload = _read_json(self)
            username = str(payload.get("username", "")).strip()
            role = SESSION.store.validate_user(username, str(payload.get("password", "")).strip())
            if role is None: return _json(self, {"ok": False, "message": "用户名或密码错误"}, status=400)
            SESSION.store.set_state(current_user=username, current_role=role)
            SESSION.reset_state()
            return _json(self, {"ok": True, "message": f"已登录：{username}", "role": role})
        if parsed.path == "/api/auth/logout":
            SESSION.store.set_state(current_user=GUEST_USER, current_role=STUDENT_ROLE)
            SESSION.reset_state()
            return _json(self, {"ok": True, "message": "已退出登录"})
        if parsed.path == "/api/auth/register":
            payload = _read_json(self)
            ok = SESSION.store.register_user(str(payload.get("username", "")).strip(), str(payload.get("password", "")).strip(), str(payload.get("role", STUDENT_ROLE)).strip() or STUDENT_ROLE)
            return _json(self, {"ok": ok, "message": "注册成功" if ok else "用户已存在或输入无效"}, status=200 if ok else 400)
        if parsed.path == "/api/auth/reset_password":
            payload = _read_json(self)
            ok = SESSION.store.reset_password(str(payload.get("username", "")).strip(), str(payload.get("password", "")).strip())
            return _json(self, {"ok": ok, "message": "密码已重置" if ok else "用户不存在"}, status=200 if ok else 400)
        if parsed.path == "/api/history/delete":
            ok = SESSION.store.delete_history(int(_read_json(self).get("id", 0)))
            return _json(self, {"ok": ok, "message": "历史记录已删除" if ok else "记录不存在"}, status=200 if ok else 404)
        if parsed.path == "/api/history/replay":
            item = SESSION.store.get_history(int(_read_json(self).get("id", 0)))
            if not item: return _json(self, {"ok": False, "message": "历史记录不存在"}, status=404)
            motion_path = item.get("npy_path") or item.get("bvh_path") or item.get("source_path")
            if not motion_path or not os.path.exists(motion_path) or not str(motion_path).lower().endswith((".npy", ".bvh")):
                return _json(self, {"ok": False, "message": "该记录没有可重评的 NPY/BVH 文件"}, status=400)
            seq = _load_mocap_sequence(motion_path)
            scorer = Scorer(dance_type=item.get("dance_type") or "黑走马 (Kara Jorga)")
            result = scorer.score_mocap_sequence(seq)
            report = _sequence_report(seq, int(result["score"]), item.get("dance_type") or "未命名舞种", str(result["feedback"]))
            new_id = SESSION.store.save_history({"username": SESSION.state["current_user"], "role": SESSION.state["current_role"], "dance_type": item.get("dance_type") or "未命名舞种", "avg_score": float(result["final"]), "best_combo": 0, "duration_sec": item.get("duration_sec") or int(len(seq) / 30), "grade": _grade(float(result["final"])), "record_text": f"历史重评：{motion_path}", "summary_report": report, "summary_image": "", "npy_path": motion_path if str(motion_path).lower().endswith(".npy") else item.get("npy_path", ""), "bvh_path": motion_path if str(motion_path).lower().endswith(".bvh") else item.get("bvh_path", ""), "source_type": "history_replay", "source_path": motion_path})
            return _json(self, {"ok": True, "message": "历史记录已重新评估", "history_id": new_id, "result": result})
        if parsed.path == "/api/import/upload": return self._handle_import_upload()
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args):
        return


def run_server(host: str = "127.0.0.1", port: int = 8000):
    httpd = ThreadingHTTPServer((host, port), WebHandler)
    print(f"Web UI running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        SESSION.stop()
        httpd.server_close()










