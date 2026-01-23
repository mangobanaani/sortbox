from src.models import (
    ClassificationResult,
    ClassifyRequest,
    ClassifyResponse,
    EmailInput,
)


def test_email_input_valid():
    email = EmailInput(
        email_id="msg001",
        sender="billing@stripe.com",
        subject="Invoice #1234",
        body_preview="Your invoice is ready.",
    )
    assert email.email_id == "msg001"
    assert email.sender == "billing@stripe.com"


def test_classification_result_defaults():
    result = ClassificationResult(email_id="msg001", labels=["invoices"])
    assert result.confidence == 1.0
    assert result.suggestion is None


def test_classification_result_with_suggestion():
    result = ClassificationResult(
        email_id="msg001",
        labels=[],
        confidence=0.3,
        suggestion="travel",
    )
    assert result.suggestion == "travel"


def test_classify_request():
    req = ClassifyRequest(
        emails=[
            EmailInput(
                email_id="msg001",
                sender="a@b.com",
                subject="Hi",
                body_preview="Hello",
            )
        ]
    )
    assert len(req.emails) == 1


def test_classify_response():
    resp = ClassifyResponse(
        results=[ClassificationResult(email_id="msg001", labels=["invoices"])]
    )
    assert len(resp.results) == 1
