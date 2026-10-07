import sqlite3

DB_FILE = "chatbot.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            preferred_language TEXT DEFAULT 'auto',
            voice_enabled INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            bot_reply TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    # Migration safety for older chats table
    try:
        cur.execute("ALTER TABLE chats ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE chats ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def create_user(username: str, password_hash: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        user_id = cur.lastrowid
        cur.execute(
            "INSERT INTO user_settings (user_id, preferred_language, voice_enabled) VALUES (?, 'auto', 0)",
            (user_id,),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save_chat(user_id: int, user_message: str, bot_reply: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chats (user_id, user_message, bot_reply, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (user_id, user_message, bot_reply),
    )
    conn.commit()
    conn.close()


def get_user_chats(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_message, bot_reply, created_at FROM chats WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_settings(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT preferred_language, voice_enabled FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"preferred_language": "auto", "voice_enabled": 0}
    return dict(row)


def update_user_settings(user_id: int, preferred_language: str, voice_enabled: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_settings (user_id, preferred_language, voice_enabled)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            preferred_language = excluded.preferred_language,
            voice_enabled = excluded.voice_enabled
        """,
        (user_id, preferred_language, voice_enabled),
    )
    conn.commit()
    conn.close()


def get_chat_count(user_id: int) -> int:
    """Get total chat count for a user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM chats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0
