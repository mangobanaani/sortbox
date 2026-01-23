from pydantic import BaseModel


class EmailInput(BaseModel):
    email_id: str
    sender: str
    subject: str
    body_preview: str


class ClassificationResult(BaseModel):
    email_id: str
    labels: list[str]
    confidence: float = 1.0
    suggestion: str | None = None


class ClassifyRequest(BaseModel):
    emails: list[EmailInput]


class ClassifyResponse(BaseModel):
    results: list[ClassificationResult]
