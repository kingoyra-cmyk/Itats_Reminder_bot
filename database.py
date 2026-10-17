import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "bot_database.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                session_cookie TEXT,
                xsrf_token TEXT,
                cf_clearance TEXT,
                user_agent TEXT,
                last_task_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                role TEXT DEFAULT 'subscriber',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        cols = [c[1] for c in cursor.fetchall()]
        if "role" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'subscriber'")
        conn.commit()

def register_subscriber(chat_id: int, name: str, username: str):
    """Mendaftarkan teman sebagai subscriber otomatis tanpa perlu login atau cari cookie"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (chat_id, name, username, is_active, role, created_at, updated_at)
            VALUES (?, ?, ?, 1, 'subscriber', ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                name = excluded.name,
                username = excluded.username,
                is_active = 1,
                updated_at = excluded.updated_at
        """, (chat_id, name, username, now, now))
        conn.commit()

def save_or_update_user(chat_id: int, name: str, username: str, session: str, xsrf: str, cf_clearance: str = "", user_agent: str = "", role: str = "member"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (chat_id, name, username, session_cookie, xsrf_token, cf_clearance, user_agent, is_active, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                name = excluded.name,
                username = excluded.username,
                session_cookie = excluded.session_cookie,
                xsrf_token = excluded.xsrf_token,
                cf_clearance = excluded.cf_clearance,
                user_agent = CASE WHEN excluded.user_agent != '' THEN excluded.user_agent ELSE users.user_agent END,
                is_active = 1,
                role = excluded.role,
                updated_at = excluded.updated_at
        """, (chat_id, name, username, session, xsrf, cf_clearance, user_agent, role, now, now))
        conn.commit()

def get_user(chat_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None

def get_admin_user():
    """Mengambil user admin/pemantau utama yang memiliki cookie sesi aktif"""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE session_cookie IS NOT NULL AND session_cookie != '' ORDER BY (role = 'admin') DESC, updated_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

def get_all_subscribers():
    """Mengambil semua teman yang aktif menerima notifikasi pengingat"""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users WHERE is_active = 1").fetchall()
        return [dict(r) for r in rows]

def get_all_active_users_with_cookie():
    """Mengambil semua user yang punya cookie sesi pribadi"""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users WHERE is_active = 1 AND session_cookie IS NOT NULL AND session_cookie != ''").fetchall()
        return [dict(r) for r in rows]

def update_user_cookies(chat_id: int, session: str, xsrf: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        if xsrf:
            conn.execute("UPDATE users SET session_cookie = ?, xsrf_token = ?, updated_at = ? WHERE chat_id = ?", (session, xsrf, now, chat_id))
        else:
            conn.execute("UPDATE users SET session_cookie = ?, updated_at = ? WHERE chat_id = ?", (session, now, chat_id))
        conn.commit()

def update_last_task_count(chat_id: int, count: int):
    with get_connection() as conn:
        conn.execute("UPDATE users SET last_task_count = ? WHERE chat_id = ?", (count, chat_id))
        conn.commit()

def set_user_status(chat_id: int, is_active: bool):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_active = ? WHERE chat_id = ?", (1 if is_active else 0, chat_id))
        conn.commit()

def delete_user(chat_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
        conn.commit()

def get_user_count():
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as total FROM users").fetchone()
        return row["total"] if row else 0

def set_user_role(chat_id: int, role: str):
    """Ubah role pengguna: admin / co-admin / custom / subscriber"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET role = ?, updated_at = ? WHERE chat_id = ?",
            (role, now, chat_id)
        )
        conn.commit()
