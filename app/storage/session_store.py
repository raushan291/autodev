import sqlite3
import json
import os
from datetime import datetime
from app.config import settings


class SessionStore:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(settings.PERSIST_DIR, "sessions.db")
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        conn.commit()
        conn.close()

    def create_session(self, session_id):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO sessions (session_id, created_at, updated_at) VALUES (?, ?, ?)",
                (session_id, now, now)
            )
        except sqlite3.IntegrityError:
            pass

        conn.commit()
        conn.close()
        return session_id

    def get_session(self, session_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT session_id, created_at, updated_at FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "session_id": result[0],
                "created_at": result[1],
                "updated_at": result[2]
            }
        return None

    def add_message(self, session_id, role, content, metadata=None):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, now, json.dumps(metadata) if metadata else None)
        )

        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id)
        )

        conn.commit()
        conn.close()

    def get_messages(self, session_id, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        results = cursor.fetchall()
        conn.close()

        messages = []
        for row in results:
            messages.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return list(reversed(messages))

    def add_user_context(self, session_id, context_type, content, metadata=None):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO user_contexts (session_id, context_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, context_type, content, now, json.dumps(metadata) if metadata else None)
        )

        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id)
        )

        conn.commit()
        conn.close()

    def get_user_contexts(self, session_id, context_type=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if context_type:
            cursor.execute(
                "SELECT context_type, content, timestamp, metadata FROM user_contexts WHERE session_id = ? AND context_type = ? ORDER BY timestamp DESC",
                (session_id, context_type)
            )
        else:
            cursor.execute(
                "SELECT context_type, content, timestamp, metadata FROM user_contexts WHERE session_id = ? ORDER BY timestamp DESC",
                (session_id,)
            )

        results = cursor.fetchall()
        conn.close()

        contexts = []
        for row in results:
            contexts.append({
                "context_type": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3]) if row[3] else None
            })

        return contexts

    def get_all_sessions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT session_id, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        results = cursor.fetchall()
        conn.close()

        sessions = []
        for row in results:
            sessions.append({
                "session_id": row[0],
                "created_at": row[1],
                "updated_at": row[2]
            })

        return sessions
