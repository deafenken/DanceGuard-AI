import hashlib
import os
import shutil
import sqlite3
import time
from typing import Any, Dict, List, Optional


GUEST_USER = "游客"
STUDENT_ROLE = "学生"
TEACHER_ROLE = "教师"
ADMIN_ROLE = "管理员"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class LocalStore:
    def __init__(self, db_path: str = os.path.join("assets", "app", "system.db")):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()
        self._ensure_defaults()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                );

                CREATE TABLE IF NOT EXISTS app_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_user TEXT,
                    current_role TEXT,
                    last_import_path TEXT
                );

                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    role TEXT,
                    dance_type TEXT,
                    avg_score REAL,
                    best_combo INTEGER,
                    duration_sec INTEGER,
                    grade TEXT,
                    record_text TEXT,
                    summary_report TEXT,
                    summary_image TEXT,
                    npy_path TEXT,
                    bvh_path TEXT,
                    source_type TEXT,
                    source_path TEXT,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    role TEXT,
                    dance_type TEXT,
                    comment TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    role TEXT,
                    src_path TEXT,
                    stored_path TEXT,
                    file_type TEXT,
                    eval_status TEXT,
                    eval_score REAL,
                    eval_grade TEXT,
                    result_history_id INTEGER,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "history", "npy_path", "TEXT DEFAULT ''")
            self._ensure_column(conn, "history", "bvh_path", "TEXT DEFAULT ''")
            self._ensure_column(conn, "history", "source_type", "TEXT DEFAULT ''")
            self._ensure_column(conn, "history", "source_path", "TEXT DEFAULT ''")
            self._ensure_column(conn, "history", "deleted", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "imports", "eval_status", "TEXT DEFAULT '已导入'")
            self._ensure_column(conn, "imports", "eval_score", "REAL")
            self._ensure_column(conn, "imports", "eval_grade", "TEXT")
            self._ensure_column(conn, "imports", "result_history_id", "INTEGER")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str):
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _ensure_defaults(self):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO app_state (id, current_user, current_role, last_import_path) VALUES (1, ?, ?, '')",
                (GUEST_USER, STUDENT_ROLE),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                ("admin", self._hash_password("admin123"), ADMIN_ROLE, _now(), _now()),
            )
            conn.execute(
                "UPDATE app_state SET current_user = ? WHERE id = 1 AND (current_user IS NULL OR current_user = '' OR current_user LIKE '娓%')",
                (GUEST_USER,),
            )
            conn.execute(
                "UPDATE app_state SET current_role = ? WHERE id = 1 AND (current_role IS NULL OR current_role = '' OR current_role LIKE '瀛%' OR current_role LIKE '鐎%')",
                (STUDENT_ROLE,),
            )
            conn.execute(
                "UPDATE users SET role = ? WHERE username = 'admin' AND role != ?",
                (ADMIN_ROLE, ADMIN_ROLE),
            )

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows]

    def get_state(self) -> Dict[str, str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT current_user, current_role, last_import_path FROM app_state WHERE id = 1"
            ).fetchone()
        return dict(row) if row else {"current_user": GUEST_USER, "current_role": STUDENT_ROLE, "last_import_path": ""}

    def set_state(
        self,
        current_user: Optional[str] = None,
        current_role: Optional[str] = None,
        last_import_path: Optional[str] = None,
    ):
        state = self.get_state()
        payload = (
            state["current_user"] if current_user is None else current_user,
            state["current_role"] if current_role is None else current_role,
            state["last_import_path"] if last_import_path is None else last_import_path,
        )
        with self._connect() as conn:
            conn.execute(
                "UPDATE app_state SET current_user = ?, current_role = ?, last_import_path = ? WHERE id = 1",
                payload,
            )

    def register_user(self, username: str, password: str, role: str) -> bool:
        if not username or not password:
            return False
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
                    (username.strip(), self._hash_password(password), role or STUDENT_ROLE, _now(), None),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def validate_user(self, username: str, password: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT role, password_hash FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if not row or row["password_hash"] != self._hash_password(password):
                return None
            conn.execute("UPDATE users SET last_login = ? WHERE username = ?", (_now(), username.strip()))
        return str(row["role"])

    def reset_password(self, username: str, new_password: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (self._hash_password(new_password), username.strip()),
            )
        return cur.rowcount > 0

    def list_users(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, role, created_at, last_login FROM users ORDER BY created_at DESC"
            ).fetchall()
        return self._rows_to_dicts(rows)

    def history_scope(self, username: str, role: str) -> Optional[str]:
        return None if role in {TEACHER_ROLE, ADMIN_ROLE} else username

    def save_history(self, payload: Dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO history (
                    username, role, dance_type, avg_score, best_combo, duration_sec, grade,
                    record_text, summary_report, summary_image, npy_path, bvh_path,
                    source_type, source_path, deleted, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    payload.get("username") or GUEST_USER,
                    payload.get("role") or STUDENT_ROLE,
                    payload.get("dance_type") or "未命名舞种",
                    payload.get("avg_score", 0.0),
                    payload.get("best_combo", 0),
                    payload.get("duration_sec", 0),
                    payload.get("grade", "C"),
                    payload.get("record_text", ""),
                    payload.get("summary_report", ""),
                    payload.get("summary_image", ""),
                    payload.get("npy_path", ""),
                    payload.get("bvh_path", ""),
                    payload.get("source_type", ""),
                    payload.get("source_path", ""),
                    _now(),
                ),
            )
            return int(cur.lastrowid)

    def list_history(
        self,
        username: Optional[str] = None,
        dance_type: str = "",
        grade: str = "",
        keyword: str = "",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM history WHERE deleted = 0"
        args: List[Any] = []
        if username and username != GUEST_USER:
            sql += " AND username = ?"
            args.append(username)
        if dance_type:
            sql += " AND dance_type = ?"
            args.append(dance_type)
        if grade:
            sql += " AND grade = ?"
            args.append(grade)
        if keyword:
            like = f"%{keyword}%"
            sql += " AND (dance_type LIKE ? OR grade LIKE ? OR record_text LIKE ? OR summary_report LIKE ? OR created_at LIKE ?)"
            args.extend([like, like, like, like, like])
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return self._rows_to_dicts(rows)

    def get_history(self, history_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM history WHERE id = ? AND deleted = 0",
                (history_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_history(self, history_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("UPDATE history SET deleted = 1 WHERE id = ?", (history_id,))
        return cur.rowcount > 0

    def save_comment(self, username: str, role: str, dance_type: str, comment: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO comments (username, role, dance_type, comment, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, role, dance_type, comment, _now()),
            )

    def latest_comment(self, username: str, dance_type: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT comment FROM comments WHERE username = ? AND dance_type = ? ORDER BY id DESC LIMIT 1",
                (username, dance_type),
            ).fetchone()
        return str(row["comment"]) if row else ""

    def save_import_record(
        self,
        username: str,
        role: str,
        src_path: str,
        stored_path: str,
        file_type: str,
        eval_status: str = "已导入",
        eval_score: Optional[float] = None,
        eval_grade: str = "",
        result_history_id: Optional[int] = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO imports (
                    username, role, src_path, stored_path, file_type,
                    eval_status, eval_score, eval_grade, result_history_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    role,
                    src_path,
                    stored_path,
                    file_type.lower(),
                    eval_status,
                    eval_score,
                    eval_grade,
                    result_history_id,
                    _now(),
                ),
            )
            return int(cur.lastrowid)

    def update_import_result(
        self,
        import_id: int,
        eval_status: str,
        eval_score: Optional[float] = None,
        eval_grade: str = "",
        result_history_id: Optional[int] = None,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE imports SET eval_status = ?, eval_score = ?, eval_grade = ?, result_history_id = ? WHERE id = ?",
                (eval_status, eval_score, eval_grade, result_history_id, import_id),
            )
        return cur.rowcount > 0

    def save_import(self, username: str, role: str, src_path: str, imports_dir: str) -> str:
        os.makedirs(imports_dir, exist_ok=True)
        name = os.path.basename(src_path)
        stem, ext = os.path.splitext(name)
        stored_name = f"{stem}_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
        stored_path = os.path.join(imports_dir, stored_name)
        shutil.copy2(src_path, stored_path)
        self.save_import_record(username, role, src_path, stored_path, ext.lower(), eval_status="已归档")
        self.set_state(last_import_path=stored_path)
        return stored_path

    def list_imports(self, username: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM imports"
        args: List[Any] = []
        if username and username != GUEST_USER:
            sql += " WHERE username = ?"
            args.append(username)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return self._rows_to_dicts(rows)

    def get_import(self, import_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
        return dict(row) if row else None
