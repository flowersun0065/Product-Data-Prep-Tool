"""
对话存储 — SQLite 实现。

本地 SQLite，未来可无缝迁移到 PostgreSQL（改这个文件即可）。
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..constants import CACHE_FOLDER

DB_PATH = CACHE_FOLDER / "agent.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表（幂等）"""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                current_session_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tool_calls TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, created_at);
        """)


def create_conversation(title: str = "", session_id: str = "") -> str:
    """创建新对话，返回 ID"""
    cid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, current_session_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (cid, title, session_id, now, now),
        )
    return cid


def get_conversation(conversation_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return dict(row) if row else None


def list_conversations(limit: int = 50) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, current_session_id, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_conversation(conversation_id: str, title: str = None, session_id: str = None):
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if session_id is not None:
        fields.append("current_session_id = ?")
        params.append(session_id)
    fields.append("updated_at = ?")
    params.append(now)
    params.append(conversation_id)
    with _get_conn() as conn:
        conn.execute(
            f"UPDATE conversations SET {', '.join(fields)} WHERE id = ?", params
        )


def add_message(conversation_id: str, role: str, content: str = "", tool_calls: list = None) -> str:
    """添加消息，返回消息 ID"""
    mid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content,
             json.dumps(tool_calls or [], ensure_ascii=False), now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
        )
    return mid


def get_messages(conversation_id: str) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content, tool_calls, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    result = []
    for r in rows:
        msg = dict(r)
        try:
            msg["tool_calls"] = json.loads(msg.get("tool_calls", "[]"))
        except (json.JSONDecodeError, TypeError):
            msg["tool_calls"] = []
        result.append(msg)
    return result
