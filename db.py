"""
数据库模块 — todos 表 + users 表
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/todo-voice-caller/todos.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            open_id TEXT PRIMARY KEY,
            phone TEXT DEFAULT '',
            name TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_open_id TEXT NOT NULL,
            content TEXT NOT NULL,
            remind_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            msg_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_open_id) REFERENCES users(open_id)
        );
        CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status, remind_time);
    """)
    conn.commit()
    conn.close()


# ─── 用户操作 ───


def get_or_create_user(open_id: str, name: str = "") -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE open_id=?", (open_id,)).fetchone()
    if row:
        conn.close()
        return dict(row)
    conn.execute("INSERT INTO users (open_id, name) VALUES (?, ?)", (open_id, name))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE open_id=?", (open_id,)).fetchone()
    conn.close()
    return dict(row)


def bind_phone(open_id: str, phone: str) -> bool:
    conn = get_conn()
    conn.execute("UPDATE users SET phone=? WHERE open_id=?", (phone, open_id))
    conn.commit()
    conn.close()
    return True


def get_user(open_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE open_id=?", (open_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── 待办操作 ───


def add_todo(user_open_id: str, content: str, remind_time: str, msg_id: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO todos (user_open_id, content, remind_time, msg_id) VALUES (?, ?, ?, ?)",
        (user_open_id, content, remind_time, msg_id),
    )
    conn.commit()
    todo_id = cur.lastrowid
    conn.close()
    return todo_id


def get_due_todos() -> list:
    """获取所有到期待提醒的待办"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.*, u.phone, u.open_id
           FROM todos t
           JOIN users u ON t.user_open_id = u.open_id
           WHERE t.status='pending' AND t.remind_time <= ?""",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_done(todo_id: int):
    conn = get_conn()
    conn.execute("UPDATE todos SET status='done' WHERE id=?", (todo_id,))
    conn.commit()
    conn.close()


def mark_failed(todo_id: int):
    conn = get_conn()
    conn.execute("UPDATE todos SET status='failed' WHERE id=?", (todo_id,))
    conn.commit()
    conn.close()


def get_user_todos(open_id: str, limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM todos WHERE user_open_id=? ORDER BY remind_time DESC LIMIT ?",
        (open_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_count(open_id: str) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM todos WHERE user_open_id=? AND status='pending'",
        (open_id,),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_weekly_summary() -> dict:
    """获取本周汇总数据"""
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done_count,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending_count
        FROM todos
        WHERE created_at >= date('now', 'weekday 0', '-7 days')
    """).fetchone()
    conn.close()
    return dict(row) if row else {"total": 0, "done_count": 0, "pending_count": 0}


def cancel_todo(todo_id: int, open_id: str) -> bool:
    """撤销指定待办（仅待办创建者可撤销）"""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE todos SET status='cancelled' WHERE id=? AND user_open_id=? AND status='pending'",
        (todo_id, open_id),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def cancel_todo_by_content(open_id: str, keyword: str) -> list:
    """通过内容关键词搜索待办并撤销，返回已撤销的数量"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id FROM todos WHERE user_open_id=? AND status='pending' AND content LIKE ?",
        (open_id, f"%{keyword}%"),
    ).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"UPDATE todos SET status='cancelled' WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()
    conn.close()
    return ids
