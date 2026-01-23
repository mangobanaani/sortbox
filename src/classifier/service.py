from pathlib import Path

from fastapi import FastAPI

from src.classifier.llm_classifier import classify_with_llm
from src.classifier.providers.base import LLMProvider
from src.classifier.rules import match_rules
from src.config import load_config
from src.database import insert_classification_event
from src.models import (
    ClassificationResult,
    ClassifyRequest,
    ClassifyResponse,
)


def create_app(
    config_path: Path | None = None,
    provider: LLMProvider | None = None,
) -> FastAPI:
    app = FastAPI(title="Sortbox")

    config_path = config_path or Path("labels.yaml")
    config = load_config(config_path)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/classify", response_model=ClassifyResponse)
    async def classify(request: ClassifyRequest) -> ClassifyResponse:
        results: list[ClassificationResult] = []
        llm_emails = []

        for email in request.emails:
            matched = match_rules(email, config.labels)
            if matched:
                result = ClassificationResult(
                    email_id=email.email_id,
                    labels=matched,
                    confidence=1.0,
                )
                results.append(result)

                # Track classification event
                if result.labels:
                    try:
                        insert_classification_event(
                            label=result.labels[0],
                            method="rule",
                            confidence=result.confidence
                        )
                    except Exception as e:
                        # Log but don't fail classification
                        print(f"Warning: Failed to track event: {e}")
            else:
                llm_emails.append(email)

        if llm_emails and provider:
            llm_results = await classify_with_llm(
                llm_emails,
                config.labels,
                provider,
                config.settings.confidence_threshold,
            )
            results.extend(llm_results)

            # Track LLM classification events
            for result in llm_results:
                if result.labels:
                    try:
                        insert_classification_event(
                            label=result.labels[0],
                            method="llm",
                            confidence=result.confidence
                        )
                    except Exception as e:
                        # Log but don't fail classification
                        print(f"Warning: Failed to track event: {e}")

        # Sort results to match input order
        order = {e.email_id: i for i, e in enumerate(request.emails)}
        results.sort(key=lambda r: order.get(r.email_id, 0))

        return ClassifyResponse(results=results)

    return app
