import shutil
from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def backup_config():
    """Backup and restore labels.yaml config."""
    config_path = Path("labels.yaml")
    backup_path = Path("labels.yaml.backup")

    # Backup original config
    shutil.copy(config_path, backup_path)

    yield config_path

    # Restore original config
    shutil.copy(backup_path, config_path)
    backup_path.unlink()


@pytest.mark.asyncio
async def test_get_labels():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/labels")
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert "settings" in data
    assert "finance" in data["labels"]


@pytest.mark.asyncio
async def test_create_label(backup_config):
    config_path = backup_config

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/labels", json={
            "name": "test-new-label",
            "description": "Test label description",
            "rules": []
        })
    assert response.status_code == 201

    # Verify the label was created
    with open(config_path) as f:
        data = yaml.safe_load(f)
    assert "test-new-label" in data["labels"]
    assert data["labels"]["test-new-label"]["description"] == "Test label description"


@pytest.mark.asyncio
async def test_update_label(backup_config):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/labels/finance",
            json={
                "description": "Updated description",
                "rules": [{"type": "from", "pattern": "*@stripe.com"}],
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_label(backup_config):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/api/labels/finance")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_classify_email():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/labels/test",
            json={
                "email": {
                    "sender": "billing@stripe.com",
                    "subject": "Invoice #1234",
                    "body_preview": "Your invoice is ready",
                }
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "matched_labels" in data
    assert "matched_rules" in data
    assert "confidence" in data
    assert "llm_used" in data
    assert "time_ms" in data

    # Verify the finance label was matched
    assert "finance" in data["matched_labels"]
    assert len(data["matched_rules"]) >= 1
    assert data["matched_rules"][0]["label"] == "finance"
    assert data["matched_rules"][0]["rule"]["type"] in ["from", "subject_contains"]
    assert data["confidence"] == 1.0
    assert data["llm_used"] is False
    assert isinstance(data["time_ms"], int)
    assert data["time_ms"] >= 0
