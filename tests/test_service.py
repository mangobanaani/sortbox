import pytest
from httpx import ASGITransport, AsyncClient

from src.classifier.providers.base import LLMClassification
from src.classifier.service import create_app


class FakeProvider:
    async def classify(self, emails, label_definitions):
        return [
            LLMClassification(label="action-required", confidence=0.9) for _ in emails
        ]


@pytest.fixture
def app(tmp_path):
    config_data = """
labels:
  invoices:
    description: "Bills"
    rules:
      - from: "*@stripe.com"
  action-required:
    description: "Needs reply"
    rules: []
settings:
  llm_provider: "claude"
  confidence_threshold: 0.7
  max_emails_per_run: 100
  suggestion_file: "suggestions.json"
"""
    config_file = tmp_path / "labels.yaml"
    config_file.write_text(config_data)
    return create_app(config_path=config_file, provider=FakeProvider())


@pytest.mark.asyncio
async def test_classify_rule_match(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/classify",
            json={
                "emails": [
                    {
                        "email_id": "msg001",
                        "sender": "billing@stripe.com",
                        "subject": "Invoice",
                        "body_preview": "Your invoice",
                    }
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["labels"] == ["invoices"]
    assert data["results"][0]["confidence"] == 1.0


@pytest.mark.asyncio
async def test_classify_llm_fallback(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/classify",
            json={
                "emails": [
                    {
                        "email_id": "msg002",
                        "sender": "boss@company.com",
                        "subject": "Meeting tomorrow",
                        "body_preview": "Can we sync?",
                    }
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["labels"] == ["action-required"]


@pytest.mark.asyncio
async def test_classify_batch_mixed(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/classify",
            json={
                "emails": [
                    {
                        "email_id": "msg001",
                        "sender": "billing@stripe.com",
                        "subject": "Invoice",
                        "body_preview": "Pay up",
                    },
                    {
                        "email_id": "msg002",
                        "sender": "friend@gmail.com",
                        "subject": "Lunch?",
                        "body_preview": "Want to grab lunch?",
                    },
                ]
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["labels"] == ["invoices"]  # rule match
    assert data["results"][1]["labels"] == ["action-required"]  # LLM


@pytest.mark.asyncio
async def test_health_endpoint(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
