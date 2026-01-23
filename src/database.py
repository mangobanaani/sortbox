"""Database layer for analytics tracking."""
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path("data/sortbox.db")


def init_database() -> None:
    """Initialize database and create tables if needed."""
    try:
        DATABASE_PATH.parent.mkdir(exist_ok=True)

        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS classification_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    label TEXT NOT NULL,
                    method TEXT NOT NULL,
                    confidence REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp "
                "ON classification_events(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_label "
                "ON classification_events(label)"
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to initialize database: {e}") from e


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection with context manager."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_classification_event(
    label: str,
    method: str,
    confidence: float
) -> None:
    """Insert a classification event.

    Args:
        label: Classification label (e.g., 'finance', 'personal').
               Must be non-empty.
        method: Classification method (e.g., 'rule', 'ml').
                Must be non-empty.
        confidence: Confidence score for the classification.
                    Must be between 0.0 and 1.0.

    Raises:
        ValueError: If label or method is empty, or confidence is out of range.
        RuntimeError: If database operation fails.
    """
    # Input validation
    if not label or not label.strip():
        raise ValueError("label must be a non-empty string")
    if not method or not method.strip():
        raise ValueError("method must be a non-empty string")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO classification_events "
                "(label, method, confidence) VALUES (?, ?, ?)",
                (label, method, confidence)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to insert classification event: {e}") from e


def count_classifications(since: datetime | None = None) -> int:
    """Count total classifications, optionally since a date."""
    with get_connection() as conn:
        if since:
            result = conn.execute(
                "SELECT COUNT(*) FROM classification_events WHERE timestamp >= ?",
                (since,)
            ).fetchone()
        else:
            result = conn.execute(
                "SELECT COUNT(*) FROM classification_events"
            ).fetchone()
        return int(result[0]) if result else 0


def get_label_counts() -> dict[str, int]:
    """Get classification count per label."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT label, COUNT(*) as count FROM classification_events GROUP BY label"
        ).fetchall()
        return {row["label"]: row["count"] for row in rows}


def count_by_method(method: str) -> int:
    """Count classifications by method (rule/llm)."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM classification_events WHERE method = ?",
            (method,)
        ).fetchone()
        return int(result[0]) if result else 0


def get_average_confidence() -> float:
    """Get average confidence across all classifications."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT AVG(confidence) FROM classification_events"
        ).fetchone()
        return result[0] if result[0] is not None else 0.0
