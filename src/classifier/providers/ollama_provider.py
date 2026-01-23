import json

from ollama import AsyncClient

from src.classifier.providers.base import LLMClassification
from src.config import LabelDefinition
from src.models import EmailInput


class OllamaProvider:
    def __init__(
        self,
        client: AsyncClient | None = None,
        model: str = "llama3",
    ):
        self._client = client or AsyncClient()
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
        response = await self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response["message"]["content"]
        parsed = json.loads(raw)
        return [LLMClassification(**item) for item in parsed]
