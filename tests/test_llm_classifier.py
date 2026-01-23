from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import TextBlock

from src.classifier.llm_classifier import classify_with_llm
from src.classifier.providers.base import LLMClassification
from src.classifier.providers.claude import ClaudeProvider
from src.classifier.providers.ollama_provider import OllamaProvider
from src.classifier.providers.openai_provider import OpenAIProvider
from src.config import LabelDefinition
from src.models import EmailInput


class MockProvider:
    def __init__(self, response: LLMClassification):
        self._response = response

    async def classify(
        self,
        emails: list[EmailInput],
        label_definitions: dict[str, LabelDefinition],
    ) -> list[LLMClassification]:
        return [self._response for _ in emails]


def _make_email(**kwargs) -> EmailInput:
    defaults = {
        "email_id": "msg001",
        "sender": "test@example.com",
        "subject": "Test subject",
        "body_preview": "Test body",
    }
    defaults.update(kwargs)
    return EmailInput(**defaults)


@pytest.mark.asyncio
async def test_classify_high_confidence():
    provider = MockProvider(LLMClassification(label="action-required", confidence=0.9))
    labels = {"action-required": LabelDefinition(description="Needs reply", rules=[])}
    results = await classify_with_llm(
        [_make_email()], labels, provider, confidence_threshold=0.7
    )
    assert results[0].labels == ["action-required"]
    assert results[0].confidence == 0.9
    assert results[0].suggestion is None


@pytest.mark.asyncio
async def test_classify_low_confidence_suggests():
    provider = MockProvider(
        LLMClassification(label="travel", confidence=0.4, suggestion="travel")
    )
    labels = {"action-required": LabelDefinition(description="Needs reply", rules=[])}
    results = await classify_with_llm(
        [_make_email()], labels, provider, confidence_threshold=0.7
    )
    assert results[0].labels == ["needs-review"]
    assert results[0].suggestion == "travel"


@pytest.mark.asyncio
async def test_classify_batch():
    provider = MockProvider(LLMClassification(label="newsletters", confidence=0.85))
    labels = {
        "newsletters": LabelDefinition(description="Subscribed content", rules=[])
    }
    emails = [_make_email(email_id=f"msg{i}") for i in range(3)]
    results = await classify_with_llm(
        emails, labels, provider, confidence_threshold=0.7
    )
    assert len(results) == 3
    assert all(r.labels == ["newsletters"] for r in results)


@pytest.mark.asyncio
async def test_claude_provider_builds_prompt():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [
        TextBlock(
            type="text",
            text='[{"label": "invoices", "confidence": 0.95, "suggestion": null}]',
        )
    ]
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    provider = ClaudeProvider(client=mock_client, model="claude-sonnet-4-20250514")
    labels = {"invoices": LabelDefinition(description="Bills", rules=[])}
    emails = [_make_email(subject="Invoice #123")]

    results = await provider.classify(emails, labels)

    assert len(results) == 1
    assert results[0].label == "invoices"
    assert results[0].confidence == 0.95
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_provider():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        '[{"label": "newsletters", "confidence": 0.88, "suggestion": null}]'
    )
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAIProvider(client=mock_client, model="gpt-4o")
    labels = {"newsletters": LabelDefinition(description="Digests", rules=[])}
    emails = [_make_email(subject="Weekly Digest")]

    results = await provider.classify(emails, labels)
    assert results[0].label == "newsletters"
    assert results[0].confidence == 0.88
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_provider():
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(
        return_value={
            "message": {
                "content": '[{"label": "notifications",'
                ' "confidence": 0.8, "suggestion": null}]'
            }
        }
    )

    provider = OllamaProvider(client=mock_client, model="llama3")
    labels = {"notifications": LabelDefinition(description="Alerts", rules=[])}
    emails = [_make_email(sender="noreply@service.com")]

    results = await provider.classify(emails, labels)
    assert results[0].label == "notifications"
    assert results[0].confidence == 0.8
    mock_client.chat.assert_called_once()
