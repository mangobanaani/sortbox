import json

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.classifier.providers.base import LLMClassification
from src.config import LabelDefinition
from src.models import EmailInput


class ClaudeProvider:
    def __init__(
        self,
        client: AsyncAnthropic | None = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self._client = client or AsyncAnthropic()
        self._model = model

    async def classify(
        self,
        emails: list[EmailInput],
        label_definitions: dict[str, LabelDefinition],
    ) -> list[LLMClassification]:
        labels_desc = "\n".join(
            f"- {name}: {defn.description}" for name, defn in label_definitions.items()
        )
        emails_desc = "\n---\n".join(
            f"ID: {e.email_id}\nFrom: {e.sender}\n"
            f"Subject: {e.subject}\nPreview: {e.body_preview}"
            for e in emails
        )
        json_fmt = (
            '{"label": "<label_name>", '
            '"confidence": <0.0-1.0>, '
            '"suggestion": "<new_label_or_null>"}'
        )
        prompt = (
            f"Classify each email into one of these labels:\n"
            f"{labels_desc}\n\n"
            f"If none fit well, suggest a new label name.\n\n"
            f"Emails:\n{emails_desc}\n\n"
            f"Respond with a JSON array. Each element: "
            f"{json_fmt}\n"
            f"Only output the JSON array, nothing else."
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text_block = response.content[0]
        if not isinstance(text_block, TextBlock):
            raise TypeError("Expected TextBlock response")
        raw = text_block.text
        parsed = json.loads(raw)
        return [LLMClassification(**item) for item in parsed]
