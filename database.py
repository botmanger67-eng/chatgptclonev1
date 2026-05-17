import sqlite3
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from config import DATABASE_PATH, SECRET_KEY  # noqa: F401  # Ensure config is loaded for environment variables

# Constants
DEFAULT_DB_PATH = DATABASE_PATH or "chat.db"
TABLE_CONVERSATIONS = "conversations"
TABLE_MESSAGES = "messages"


def get_db_path() -> str:
    """Return the path to the SQLite database file."""
    return os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Create and return a new database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create the database tables if they do not exist."""
    try:
        with get_connection() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_CONVERSATIONS} (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New Chat',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_MESSAGES} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (conversation_id) REFERENCES {TABLE_CONVERSATIONS}(id) ON DELETE CASCADE
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON {TABLE_MESSAGES}(conversation_id)
            """)
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to initialize database: {e}")


def create_conversation(conversation_id: str, title: str = "New Chat") -> bool:
    """Insert a new conversation record.

    Args:
        conversation_id: Unique identifier for the conversation.
        title: Display title for the conversation.

    Returns:
        True if insertion succeeded, False otherwise.

    Raises:
        RuntimeError: On database errors.
    """
    try:
        with get_connection() as conn:
            conn.execute(
                f"INSERT INTO {TABLE_CONVERSATIONS} (id, title) VALUES (?, ?)",
                (conversation_id, title),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # Conversation already exists – not an error for most cases
        return False
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to create conversation: {e}")


def get_conversation(conversation_id: str) -> Optional[Dict[str, str]]:
    """Fetch a single conversation by its ID.

    Args:
        conversation_id: The conversation's unique ID.

    Returns:
        A dictionary with 'id', 'title', 'created_at', 'updated_at'
        or None if not found.
    """
    try:
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT id, title, created_at, updated_at FROM {TABLE_CONVERSATIONS} WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get conversation: {e}")


def get_all_conversations(order: str = "desc") -> List[Dict[str, str]]:
    """Retrieve all conversations, ordered by updated_at.

    Args:
        order: 'desc' (newest first) or 'asc' (oldest first).

    Returns:
        List of conversation dictionaries.
    """
    try:
        order_clause = "DESC" if order.lower() == "desc" else "ASC"
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT id, title, created_at, updated_at FROM {TABLE_CONVERSATIONS} ORDER BY updated_at {order_clause}"
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get all conversations: {e}")


def update_conversation_title(conversation_id: str, title: str) -> bool:
    """Update the title of an existing conversation.

    Args:
        conversation_id: The conversation ID.
        title: New title string.

    Returns:
        True if update succeeded, False if conversation not found.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE {TABLE_CONVERSATIONS} SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (title, conversation_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to update conversation title: {e}")


def delete_conversation(conversation_id: str) -> bool:
    """Remove a conversation and all its messages (cascade).

    Args:
        conversation_id: The conversation ID.

    Returns:
        True if deletion succeeded, False if not found.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM {TABLE_CONVERSATIONS} WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to delete conversation: {e}")


def add_message(conversation_id: str, role: str, content: str) -> int:
    """Insert a new message into the database.

    Args:
        conversation_id: The conversation ID.
        role: 'user', 'assistant', or 'system'.
        content: The message text.

    Returns:
        The auto‑generated message ID.

    Raises:
        ValueError: If role is invalid.
    """
    valid_roles = {"user", "assistant", "system"}
    if role not in valid_roles:
        raise ValueError(f"Invalid role '{role}'. Must be one of {valid_roles}")

    try:
        with get_connection() as conn:
            # Ensure conversation exists; create if not
            if not get_conversation(conversation_id):
                create_conversation(conversation_id)

            cursor = conn.execute(
                f"INSERT INTO {TABLE_MESSAGES} (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )
            # Update the conversation's updated_at timestamp
            conn.execute(
                f"UPDATE {TABLE_CONVERSATIONS} SET updated_at = datetime('now') WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to add message: {e}")


def get_messages_by_conversation(
    conversation_id: str, order: str = "asc"
) -> List[Dict[str, str]]:
    """Retrieve all messages for a given conversation.

    Args:
        conversation_id: The conversation ID.
        order: 'asc' (chronological) or 'desc' (newest first).

    Returns:
        List of message dictionaries with keys 'id', 'role', 'content', 'timestamp'.
    """
    try:
        order_clause = "ASC" if order.lower() == "asc" else "DESC"
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT id, role, content, timestamp FROM {TABLE_MESSAGES} "
                f"WHERE conversation_id = ? ORDER BY timestamp {order_clause}",
                (conversation_id,),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get messages: {e}")


def get_last_n_messages(conversation_id: str, n: int = 20) -> List[Dict[str, str]]:
    """Get the most recent `n` messages in chronological order.

    Args:
        conversation_id: The conversation ID.
        n: Maximum number of messages to return.

    Returns:
        List of message dictionaries in chronological order.
    """
    try:
        with get_connection() as conn:
            # Subquery to get the latest n messages, then order ascending
            rows = conn.execute(
                f"""
                SELECT * FROM (
                    SELECT id, role, content, timestamp
                    FROM {TABLE_MESSAGES}
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ) ORDER BY timestamp ASC
                """,
                (conversation_id, n),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to get last n messages: {e}")


def search_conversations(query: str) -> List[Dict[str, str]]:
    """Search conversations by title (case‑insensitive).

    Args:
        query: Search term.

    Returns:
        List of matching conversation dictionaries.
    """
    try:
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT id, title, created_at, updated_at FROM {TABLE_CONVERSATIONS} WHERE title LIKE ? ORDER BY updated_at DESC",
                (f"%{query}%",),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to search conversations: {e}")


def cleanup_old_conversations(keep_days: int = 30) -> int:
    """Delete conversations older than `keep_days` days.

    Args:
        keep_days: Number of days to retain.

    Returns:
        Number of deleted conversations.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM {TABLE_CONVERSATIONS} WHERE updated_at < datetime('now', ?)",
                (f"-{keep_days} days",),
            )
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to cleanup old conversations: {e}")


# Initialize the database when the module is imported
init_db()