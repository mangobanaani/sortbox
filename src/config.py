from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class Rule(BaseModel):
    from_pattern: str | None = None
    subject_contains: list[str] | None = None
    header_list_unsubscribe: bool | None = None

    def __init__(self, **data: Any) -> None:
        # Remap 'from' key to 'from_pattern' since 'from' is reserved
        if "from" in data:
            data["from_pattern"] = data.pop("from")
        super().__init__(**data)


class LabelDefinition(BaseModel):
    description: str
    rules: list[Rule]


class Settings(BaseModel):
    llm_provider: str = "claude"
    confidence_threshold: float = 0.7
    max_emails_per_run: int = 100
    suggestion_file: str = "suggestions.json"


class LabelConfig(BaseModel):
    labels: dict[str, LabelDefinition]
    settings: Settings


def load_config(path: Path) -> LabelConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return LabelConfig(**data)
