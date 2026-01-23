import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.database import init_database, insert_classification_event
from src.main import app


@pytest.mark.asyncio
async def test_get_analytics():
    """Test GET /api/analytics endpoint."""
    # Setup test database
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert test data
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            # Test endpoint
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_all_time"] == 2
            assert data["rule_classifications"] == 1
            assert data["llm_classifications"] == 1
            assert data["avg_confidence"] == 0.9
            assert "finance" in data["by_label"]
            assert data["by_label"]["finance"] == 1
        finally:
            src.database.DATABASE_PATH = original_path


@pytest.mark.asyncio
async def test_get_analytics_empty_database():
    """Test GET /api/analytics endpoint with empty database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Test endpoint with no data
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_all_time"] == 0
            assert data["total_today"] == 0
            assert data["total_this_week"] == 0
            assert data["by_label"] == {}
            assert data["rule_classifications"] == 0
            assert data["llm_classifications"] == 0
            assert data["avg_confidence"] == 0.0
        finally:
            src.database.DATABASE_PATH = original_path


@pytest.mark.asyncio
async def test_get_analytics_time_filtered():
    """Test GET /api/analytics endpoint with time-filtered counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert events directly into database with specific timestamps
            conn = src.database.sqlite3.connect(src.database.DATABASE_PATH)

            # Event from 10 days ago (should not count in today or this_week)
            old_timestamp = datetime.now(UTC) - timedelta(days=10)
            conn.execute(
                "INSERT INTO classification_events "
                "(timestamp, label, method, confidence) VALUES (?, ?, ?, ?)",
                (old_timestamp, "finance", "rule", 1.0)
            )

            # Event from 3 days ago (should count in this_week but not today)
            week_timestamp = datetime.now(UTC) - timedelta(days=3)
            conn.execute(
                "INSERT INTO classification_events "
                "(timestamp, label, method, confidence) VALUES (?, ?, ?, ?)",
                (week_timestamp, "newsletters", "llm", 0.8)
            )

            # Event from today (should count in both today and this_week)
            today_timestamp = datetime.now(UTC) - timedelta(hours=2)
            conn.execute(
                "INSERT INTO classification_events "
                "(timestamp, label, method, confidence) VALUES (?, ?, ?, ?)",
                (today_timestamp, "personal", "rule", 0.95)
            )

            conn.commit()
            conn.close()

            # Test endpoint
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_all_time"] == 3
            assert data["total_today"] == 1
            assert data["total_this_week"] == 2
        finally:
            src.database.DATABASE_PATH = original_path


@pytest.mark.asyncio
async def test_get_analytics_database_error():
    """Test GET /api/analytics endpoint handles database errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Mock count_classifications to raise an exception
            with patch(
                'src.api.analytics.count_classifications',
                side_effect=Exception("Database error")
            ):
                async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                    response = await client.get("/api/analytics")

                assert response.status_code == 500
                data = response.json()
                assert "Failed to retrieve analytics" in data["detail"]
        finally:
            src.database.DATABASE_PATH = original_path
