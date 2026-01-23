import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.database import (
    count_by_method,
    count_classifications,
    get_average_confidence,
    get_connection,
    get_label_counts,
    init_database,
    insert_classification_event,
)


def test_init_database_creates_table():
    """Test that database initialization creates the classification_events table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override DATABASE_PATH for test
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Verify table exists
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='classification_events'"
                )
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "classification_events"
        finally:
            src.database.DATABASE_PATH = original_path


def test_init_database_creates_indexes():
    """Test that database initialization creates the required indexes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Verify indexes exist
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='classification_events'"
                )
                indexes = [row[0] for row in cursor.fetchall()]
                assert "idx_timestamp" in indexes
                assert "idx_label" in indexes
        finally:
            src.database.DATABASE_PATH = original_path


def test_init_database_idempotency():
    """Test that calling init_database multiple times is safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            # Call init_database twice
            init_database()
            init_database()

            # Verify table still exists and works
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='classification_events'"
                )
                result = cursor.fetchone()
                assert result is not None
        finally:
            src.database.DATABASE_PATH = original_path


def test_get_connection_error_handling():
    """Test that get_connection handles errors properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        # Set to invalid path (inside a file, not a directory)
        test_file = Path(tmpdir) / "file.txt"
        test_file.write_text("test")
        src.database.DATABASE_PATH = test_file / "invalid.db"

        try:
            with pytest.raises(sqlite3.OperationalError):
                with get_connection():
                    pass
        finally:
            src.database.DATABASE_PATH = original_path


def test_insert_classification_event():
    """Test inserting a classification event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert event
            insert_classification_event("finance", "rule", 1.0)

            # Verify it was inserted
            with get_connection() as conn:
                cursor = conn.execute("SELECT * FROM classification_events")
                row = cursor.fetchone()
                assert row is not None
                assert row["label"] == "finance"
                assert row["method"] == "rule"
                assert row["confidence"] == 1.0
        finally:
            src.database.DATABASE_PATH = original_path


def test_insert_classification_event_validation():
    """Test that insert_classification_event validates inputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Test empty label
            with pytest.raises(ValueError, match="label must be a non-empty string"):
                insert_classification_event("", "rule", 1.0)

            # Test whitespace-only label
            with pytest.raises(ValueError, match="label must be a non-empty string"):
                insert_classification_event("   ", "rule", 1.0)

            # Test empty method
            with pytest.raises(ValueError, match="method must be a non-empty string"):
                insert_classification_event("finance", "", 1.0)

            # Test whitespace-only method
            with pytest.raises(ValueError, match="method must be a non-empty string"):
                insert_classification_event("finance", "   ", 1.0)

            # Test confidence below range
            with pytest.raises(
                ValueError, match="confidence must be between 0.0 and 1.0"
            ):
                insert_classification_event("finance", "rule", -0.1)

            # Test confidence above range
            with pytest.raises(
                ValueError, match="confidence must be between 0.0 and 1.0"
            ):
                insert_classification_event("finance", "rule", 1.1)

            # Verify no invalid data was inserted
            with get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM classification_events")
                count = cursor.fetchone()[0]
                assert count == 0
        finally:
            src.database.DATABASE_PATH = original_path


def test_insert_classification_event_edge_cases():
    """Test inserting classification events with edge case values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Test minimum confidence
            insert_classification_event("finance", "rule", 0.0)

            # Test maximum confidence
            insert_classification_event("personal", "ml", 1.0)

            # Test mid-range confidence
            insert_classification_event("work", "hybrid", 0.5)

            # Verify all were inserted
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT label, method, confidence FROM "
                    "classification_events ORDER BY id"
                )
                rows = cursor.fetchall()
                assert len(rows) == 3
                assert rows[0]["label"] == "finance"
                assert rows[0]["confidence"] == 0.0
                assert rows[1]["label"] == "personal"
                assert rows[1]["confidence"] == 1.0
                assert rows[2]["label"] == "work"
                assert rows[2]["confidence"] == 0.5
        finally:
            src.database.DATABASE_PATH = original_path


def test_insert_classification_event_multiple():
    """Test inserting multiple classification events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert multiple events
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("personal", "ml", 0.8)
            insert_classification_event("work", "hybrid", 0.9)

            # Verify all were inserted
            with get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM classification_events")
                count = cursor.fetchone()[0]
                assert count == 3

                # Verify order and content
                cursor = conn.execute(
                    "SELECT label, method, confidence FROM "
                    "classification_events ORDER BY id"
                )
                rows = cursor.fetchall()
                assert rows[0]["label"] == "finance"
                assert rows[0]["method"] == "rule"
                assert rows[1]["label"] == "personal"
                assert rows[1]["method"] == "ml"
                assert rows[2]["label"] == "work"
                assert rows[2]["method"] == "hybrid"
        finally:
            src.database.DATABASE_PATH = original_path


def test_insert_classification_event_timestamp():
    """Test that timestamp is auto-populated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert event
            insert_classification_event("finance", "rule", 1.0)

            # Verify timestamp was auto-populated
            with get_connection() as conn:
                cursor = conn.execute("SELECT timestamp FROM classification_events")
                row = cursor.fetchone()
                assert row is not None
                assert row["timestamp"] is not None
                # Timestamp should be a valid datetime string
                assert len(row["timestamp"]) > 0
        finally:
            src.database.DATABASE_PATH = original_path


def test_count_classifications():
    """Test counting total classifications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            total = count_classifications()
            assert total == 2
        finally:
            src.database.DATABASE_PATH = original_path


def test_count_classifications_with_date_filter():
    """Test counting classifications since a specific date."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)

            # Count since yesterday (should include the event)
            yesterday = datetime.now() - timedelta(days=1)
            count = count_classifications(since=yesterday)
            assert count == 1

            # Count since tomorrow (should be 0)
            tomorrow = datetime.now() + timedelta(days=1)
            count = count_classifications(since=tomorrow)
            assert count == 0
        finally:
            src.database.DATABASE_PATH = original_path


def test_get_label_counts():
    """Test getting classification counts per label."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            counts = get_label_counts()
            assert counts["finance"] == 2
            assert counts["newsletters"] == 1
        finally:
            src.database.DATABASE_PATH = original_path


def test_count_by_method():
    """Test counting classifications by method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            rule_count = count_by_method("rule")
            llm_count = count_by_method("llm")
            assert rule_count == 2
            assert llm_count == 1
        finally:
            src.database.DATABASE_PATH = original_path


def test_get_average_confidence():
    """Test calculating average confidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database

        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            avg = get_average_confidence()
            assert avg == 0.9  # (1.0 + 0.8) / 2
        finally:
            src.database.DATABASE_PATH = original_path
