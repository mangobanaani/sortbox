"""Integration tests for the complete Label Management UI CRUD flow.

This tests the full lifecycle of label management through the API:
1. List all labels
2. Create a new label
3. Verify creation
4. Update the label
5. Verify update
6. Test classification with the label
7. Delete the label
8. Verify deletion
"""
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
async def test_full_crud_flow(backup_config):
    """Test the complete CRUD flow for label management."""
    config_path = backup_config

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Step 1: List all labels (GET /api/labels)
        response = await client.get("/api/labels")
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "settings" in data

        initial_label_count = len(data["labels"])
        assert initial_label_count > 0  # Should have some default labels

        # Step 2: Create a new label (POST /api/labels)
        new_label_name = "test-integration-label"
        create_response = await client.post("/api/labels", json={
            "name": new_label_name,
            "description": "Integration test label for automated emails",
            "rules": [
                {
                    "type": "from",
                    "pattern": "*@test-automation.com"
                },
                {
                    "type": "subject_contains",
                    "keywords": ["automated", "test"]
                }
            ]
        })
        assert create_response.status_code == 201
        create_data = create_response.json()
        assert "message" in create_data
        assert new_label_name in create_data["message"]

        # Step 3: Verify the label was created
        response = await client.get("/api/labels")
        assert response.status_code == 200
        data = response.json()
        assert len(data["labels"]) == initial_label_count + 1
        assert new_label_name in data["labels"]

        created_label = data["labels"][new_label_name]
        expected_desc = "Integration test label for automated emails"
        assert created_label["description"] == expected_desc
        assert len(created_label["rules"]) == 2

        # Verify rules
        rule_types = [rule["type"] for rule in created_label["rules"]]
        assert "from" in rule_types
        assert "subject_contains" in rule_types

        from_rule = next(r for r in created_label["rules"] if r["type"] == "from")
        assert from_rule["pattern"] == "*@test-automation.com"

        subject_rule = next(
            r for r in created_label["rules"]
            if r["type"] == "subject_contains"
        )
        assert "automated" in subject_rule["keywords"]
        assert "test" in subject_rule["keywords"]

        # Step 4: Update the label (PUT /api/labels/{name})
        update_response = await client.put(f"/api/labels/{new_label_name}", json={
            "description": "Updated integration test label",
            "rules": [
                {
                    "type": "from",
                    "pattern": "*@updated-automation.com"
                },
                {
                    "type": "subject_contains",
                    "keywords": ["updated", "automated", "test"]
                },
                {
                    "type": "header_list_unsubscribe"
                }
            ]
        })
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert "message" in update_data
        assert new_label_name in update_data["message"]

        # Step 5: Verify the update worked
        response = await client.get("/api/labels")
        assert response.status_code == 200
        data = response.json()
        updated_label = data["labels"][new_label_name]

        assert updated_label["description"] == "Updated integration test label"
        assert len(updated_label["rules"]) == 3

        # Verify updated rules
        rule_types = [rule["type"] for rule in updated_label["rules"]]
        assert "from" in rule_types
        assert "subject_contains" in rule_types
        assert "header_list_unsubscribe" in rule_types

        from_rule = next(r for r in updated_label["rules"] if r["type"] == "from")
        assert from_rule["pattern"] == "*@updated-automation.com"

        subject_rule = next(
            r for r in updated_label["rules"]
            if r["type"] == "subject_contains"
        )
        assert "updated" in subject_rule["keywords"]
        assert len(subject_rule["keywords"]) == 3

        # Step 6: Test classification with the new label (POST /api/labels/test)
        test_response = await client.post("/api/labels/test", json={
            "email": {
                "sender": "notification@updated-automation.com",
                "subject": "Updated automated test report",
                "body_preview": "This is a test email for classification"
            }
        })
        assert test_response.status_code == 200
        test_data = test_response.json()

        assert "matched_labels" in test_data
        assert "matched_rules" in test_data
        assert "confidence" in test_data
        assert "llm_used" in test_data
        assert "time_ms" in test_data

        # Verify our label was matched
        assert new_label_name in test_data["matched_labels"]
        assert len(test_data["matched_rules"]) >= 1

        # Verify the matched rule details
        matched_rule = next(
            r for r in test_data["matched_rules"]
            if r["label"] == new_label_name
        )
        assert matched_rule["rule"]["type"] in ["from", "subject_contains"]

        # Rule-based match should have 100% confidence
        assert test_data["confidence"] == 1.0
        assert test_data["llm_used"] is False
        assert isinstance(test_data["time_ms"], int)
        assert test_data["time_ms"] >= 0

        # Step 7: Delete the label (DELETE /api/labels/{name})
        delete_response = await client.delete(f"/api/labels/{new_label_name}")
        assert delete_response.status_code == 204

        # Step 8: Verify deletion
        response = await client.get("/api/labels")
        assert response.status_code == 200
        data = response.json()
        assert len(data["labels"]) == initial_label_count
        assert new_label_name not in data["labels"]

        # Verify config file was updated correctly
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        assert new_label_name not in config_data["labels"]

        # Verify settings are still intact
        assert "settings" in config_data
        assert config_data["settings"]["llm_provider"] in ["claude", "openai", "ollama"]


@pytest.mark.asyncio
async def test_error_cases(backup_config):
    """Test error handling in the API."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Test creating duplicate label
        duplicate_response = await client.post("/api/labels", json={
            "name": "finance",  # Already exists
            "description": "Duplicate label",
            "rules": []
        })
        assert duplicate_response.status_code == 400
        assert "already exists" in duplicate_response.json()["detail"]

        # Test updating non-existent label
        update_response = await client.put("/api/labels/nonexistent-label", json={
            "description": "Updated",
            "rules": []
        })
        assert update_response.status_code == 404
        assert "not found" in update_response.json()["detail"]

        # Test deleting non-existent label
        delete_response = await client.delete("/api/labels/nonexistent-label")
        assert delete_response.status_code == 404
        assert "not found" in delete_response.json()["detail"]
