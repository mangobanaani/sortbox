import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, status

from src.api.models import (
    CreateLabelRequest,
    LabelResponse,
    LabelsResponse,
    MatchedRule,
    RuleResponse,
    TestEmailRequest,
    TestEmailResponse,
    UpdateLabelRequest,
)
from src.classifier.rules import match_rules
from src.config import Rule, load_config
from src.models import EmailInput

router = APIRouter(prefix="/api/labels", tags=["labels"])


def _rule_to_response(rule: Rule) -> RuleResponse:
    if rule.from_pattern:
        return RuleResponse(type="from", pattern=rule.from_pattern)
    elif rule.subject_contains:
        return RuleResponse(type="subject_contains", keywords=rule.subject_contains)
    elif rule.header_list_unsubscribe:
        return RuleResponse(type="header_list_unsubscribe")
    else:
        return RuleResponse(type="unknown")


@router.get("", response_model=LabelsResponse)
async def get_labels() -> LabelsResponse:
    config = load_config(Path("labels.yaml"))

    labels_dict = {
        name: LabelResponse(
            description=label.description,
            rules=[_rule_to_response(rule) for rule in label.rules],
        )
        for name, label in config.labels.items()
    }

    settings_dict = {
        "llm_provider": config.settings.llm_provider,
        "confidence_threshold": config.settings.confidence_threshold,
        "max_emails_per_run": config.settings.max_emails_per_run,
    }

    return LabelsResponse(labels=labels_dict, settings=settings_dict)


@router.post("", status_code=201)
async def create_label(request: CreateLabelRequest) -> dict[str, str]:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label already exists
    if request.name in config.labels:
        raise HTTPException(
            status_code=400, detail=f"Label '{request.name}' already exists"
        )

    # Load raw YAML to preserve formatting
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Add new label
    rules_list: list[dict[str, Any]] = []
    for rule in request.rules:
        rule_dict: dict[str, Any] = {}
        if rule.type == "from":
            rule_dict["from"] = rule.pattern
        elif rule.type == "subject_contains":
            rule_dict["subject_contains"] = rule.keywords
        elif rule.type == "header_list_unsubscribe":
            rule_dict["header_list_unsubscribe"] = True
        rules_list.append(rule_dict)

    new_label = {"description": request.description, "rules": rules_list}

    data["labels"][request.name] = new_label

    # Write back to file
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    return {"message": f"Label '{request.name}' created"}


@router.put("/{name}")
async def update_label(name: str, request: UpdateLabelRequest) -> dict[str, str]:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label exists
    if name not in config.labels:
        raise HTTPException(status_code=404, detail=f"Label '{name}' not found")

    # Load raw YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Update label
    rules_list: list[dict[str, Any]] = []
    for rule in request.rules:
        rule_dict: dict[str, Any] = {}
        if rule.type == "from":
            rule_dict["from"] = rule.pattern
        elif rule.type == "subject_contains":
            rule_dict["subject_contains"] = rule.keywords
        elif rule.type == "header_list_unsubscribe":
            rule_dict["header_list_unsubscribe"] = True
        rules_list.append(rule_dict)

    updated_label = {"description": request.description, "rules": rules_list}

    data["labels"][name] = updated_label

    # Write back
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    return {"message": f"Label '{name}' updated"}


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(name: str) -> None:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label exists
    if name not in config.labels:
        raise HTTPException(status_code=404, detail=f"Label '{name}' not found")

    # Load raw YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Delete label
    del data["labels"][name]

    # Write back
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


@router.post("/test", response_model=TestEmailResponse)
async def test_email_classification(request: TestEmailRequest) -> TestEmailResponse:
    start_time = time.time()

    config = load_config(Path("labels.yaml"))

    # Create EmailInput from request
    email = EmailInput(
        email_id="test",
        sender=request.email["sender"],
        subject=request.email["subject"],
        body_preview=request.email.get("body_preview", ""),
    )

    # Try rule matching first
    matched_labels = match_rules(email, config.labels)

    # Build matched rules list
    matched_rules_list = []
    for label_name in matched_labels:
        label_def = config.labels[label_name]
        for rule in label_def.rules:
            # Check if this rule matches
            if rule.from_pattern and email.sender:
                import fnmatch

                if fnmatch.fnmatch(email.sender.lower(), rule.from_pattern.lower()):
                    matched_rules_list.append(
                        MatchedRule(label=label_name, rule=_rule_to_response(rule))
                    )
            elif rule.subject_contains:
                subject_lower = email.subject.lower()
                if any(kw.lower() in subject_lower for kw in rule.subject_contains):
                    matched_rules_list.append(
                        MatchedRule(label=label_name, rule=_rule_to_response(rule))
                    )

    time_ms = int((time.time() - start_time) * 1000)

    return TestEmailResponse(
        matched_labels=matched_labels,
        matched_rules=matched_rules_list,
        confidence=1.0 if matched_labels else 0.0,
        llm_used=False,
        time_ms=time_ms,
    )
