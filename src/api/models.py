import re

from pydantic import BaseModel, field_validator


class RuleResponse(BaseModel):
    type: str
    pattern: str | None = None
    keywords: list[str] | None = None


class LabelResponse(BaseModel):
    description: str
    rules: list[RuleResponse]


class LabelsResponse(BaseModel):
    labels: dict[str, LabelResponse]
    settings: dict[str, str | int | float]


class RuleRequest(BaseModel):
    type: str
    pattern: str | None = None
    keywords: list[str] | None = None


class CreateLabelRequest(BaseModel):
    name: str
    description: str
    rules: list[RuleRequest] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError(
                "Label name must be lowercase alphanumeric with hyphens only"
            )
        return v


class UpdateLabelRequest(BaseModel):
    description: str
    rules: list[RuleRequest]


class TestEmailRequest(BaseModel):
    email: dict[str, str]  # sender, subject, body_preview


class MatchedRule(BaseModel):
    label: str
    rule: RuleResponse


class TestEmailResponse(BaseModel):
    matched_labels: list[str]
    matched_rules: list[MatchedRule]
    confidence: float
    llm_used: bool
    time_ms: int


class AnalyticsResponse(BaseModel):
    total_all_time: int
    total_today: int
    total_this_week: int
    by_label: dict[str, int]
    rule_classifications: int
    llm_classifications: int
    avg_confidence: float
