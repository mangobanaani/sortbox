from typing import Protocol

from pydantic import BaseModel

from src.config import LabelDefinition
from src.models import EmailInput


class LLMClassification(BaseModel):
    label: str
    confidence: float
    suggestion: str | None = None


class LLMProvider(Protocol):
    async def classify(
        self,
        emails: list[EmailInput],
        label_definitions: dict[str, LabelDefinition],
    ) -> list[LLMClassification]: ...
