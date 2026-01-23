from src.classifier.providers.base import LLMProvider
from src.config import LabelDefinition
from src.models import ClassificationResult, EmailInput


async def classify_with_llm(
    emails: list[EmailInput],
    label_definitions: dict[str, LabelDefinition],
    provider: LLMProvider,
    confidence_threshold: float,
) -> list[ClassificationResult]:
    llm_results = await provider.classify(emails, label_definitions)
    results = []
    for email, llm_result in zip(emails, llm_results, strict=True):
        if llm_result.confidence >= confidence_threshold:
            results.append(
                ClassificationResult(
                    email_id=email.email_id,
                    labels=[llm_result.label],
                    confidence=llm_result.confidence,
                )
            )
        else:
            results.append(
                ClassificationResult(
                    email_id=email.email_id,
                    labels=["needs-review"],
                    confidence=llm_result.confidence,
                    suggestion=llm_result.suggestion,
                )
            )
    return results
