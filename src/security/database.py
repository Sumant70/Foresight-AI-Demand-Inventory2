"""
Security Database Manager for Foresight AI.
Python Standard Library (sqlite3) only.
Manages users.db, schema initialization, parameterized queries, and transactions.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "users.db"


class SecurityDatabase:
    """Manages SQLite storage for users, sessions, password resets, and audit logs."""

    def __init__(self, db_path: Optional[Any] = None):
        if str(db_path) == ":memory:":
            self.db_path = ":memory:"
            self._mem_conn = sqlite3.connect(":memory:", timeout=10.0)
            self._mem_conn.execute("PRAGMA foreign_keys = ON")
            self._mem_conn.row_factory = sqlite3.Row
        else:
            self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
            self._mem_conn = None
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection with foreign keys enabled and row factory."""
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn


    def init_db(self):
        """Initializes database tables and indexes."""
        with self.get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'ANALYST', 'VIEWER')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );
            """)

            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Password reset tokens table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Audit logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    details TEXT
                );
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);")

    # -------------------------------------------------------------
    # User Operations
    # -------------------------------------------------------------
    def create_user(self, username: str, email: str, password_hash: str, password_salt: str, role: str) -> int:
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO users (username, email, password_hash, password_salt, role, is_active, failed_login_attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)
            """, (username.strip().lower(), email.strip().lower(), password_hash, password_salt, role.upper(), now, now))
            return cursor.lastrowid

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_by_username_or_email(self, identifier: str) -> Optional[Dict[str, Any]]:
        clean_id = identifier.strip().lower()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (clean_id, clean_id)
            ).fetchone()
            return dict(row) if row else None

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns all users without exposing password hashes or salts."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, username, email, role, is_active, failed_login_attempts, locked_until, created_at, updated_at, last_login_at
                FROM users ORDER BY id ASC
            """).fetchall()
            return [dict(r) for r in rows]

    def update_user_status(self, user_id: int, is_active: bool):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if is_active else 0, now, user_id)
            )

    def update_user_role(self, user_id: int, role: str):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
                (role.upper(), now, user_id)
            )

    def update_password(self, user_id: int, new_hash: str, new_salt: str):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE users
                SET password_hash = ?, password_salt = ?, updated_at = ?, failed_login_attempts = 0, locked_until = NULL
                WHERE id = ?
            """, (new_hash, new_salt, now, user_id))

    def record_login_success(self, user_id: int):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE users
                SET last_login_at = ?, failed_login_attempts = 0, locked_until = NULL
                WHERE id = ?
            """, (now, user_id))

    def record_login_failure(self, user_id: int, lock_until: Optional[str] = None):
        with self.get_connection() as conn:
            if lock_until:
                conn.execute("""
                    UPDATE users
                    SET failed_login_attempts = failed_login_attempts + 1, locked_until = ?
                    WHERE id = ?
                """, (lock_until, user_id))
            else:
                conn.execute("""
                    UPDATE users
                    SET failed_login_attempts = failed_login_attempts + 1
                    WHERE id = ?
                """, (user_id,))

    def unlock_user(self, user_id: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,))

    # -------------------------------------------------------------
    # Session Operations
    # -------------------------------------------------------------
    def create_session(self, session_id: str, user_id: int, csrf_token: str, expires_at: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, user_id, csrf_token, created_at, expires_at, last_activity, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, user_id, csrf_token, now, expires_at, now, ip_address, user_agent))

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT s.*, u.username, u.email, u.role, u.is_active, u.locked_until
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = ?
            """, (session_id,)).fetchone()
            return dict(row) if row else None

    def update_session_activity(self, session_id: str, new_last_activity: str, new_expires_at: Optional[str] = None):
        with self.get_connection() as conn:
            if new_expires_at:
                conn.execute("UPDATE sessions SET last_activity = ?, expires_at = ? WHERE session_id = ?",
                             (new_last_activity, new_expires_at, session_id))
            else:
                conn.execute("UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                             (new_last_activity, session_id))

    def delete_session(self, session_id: str):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def delete_all_user_sessions(self, user_id: int):
        """Invalidates all sessions for a user (e.g. after password change)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def clean_expired_sessions(self):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))

    def count_active_sessions(self) -> int:
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM sessions WHERE expires_at >= ?", (now,)).fetchone()
            return row["cnt"] if row else 0

    # -------------------------------------------------------------
    # Audit Logging Operations
    # -------------------------------------------------------------
    def log_audit_event(self, event: str, user_id: Optional[int] = None, ip_address: Optional[str] = None, details: Optional[str] = None):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs (user_id, event, timestamp, ip_address, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, event, now, ip_address, details))

    def get_recent_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT a.*, u.username, u.role
                FROM audit_logs a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_security_metrics(self) -> Dict[str, Any]:
        """Returns security status summary for the Admin dashboard."""
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            active_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_active = 1").fetchone()["c"]
            locked_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE locked_until > ?", (now,)).fetchone()["c"]
            active_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions WHERE expires_at >= ?", (now,)).fetchone()["c"]
            recent_failures = conn.execute(
                "SELECT COUNT(*) as c FROM audit_logs WHERE event = 'LOGIN_FAILURE' AND timestamp > datetime('now', '-24 hours')"
            ).fetchone()["c"]

            return {
                "total_users": total_users,
                "active_users": active_users,
                "locked_users": locked_users,
                "active_sessions": active_sessions,
                "recent_login_failures_24h": recent_failures,
                "system_status": "SECURE",
            }
