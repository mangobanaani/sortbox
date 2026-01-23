from pathlib import Path

import pytest
import yaml

from src.config import LabelDefinition, load_config


def test_load_config_from_yaml(tmp_path):
    config_data = {
        "labels": {
            "invoices": {
                "description": "Bills and receipts",
                "rules": [
                    {"from": "*@stripe.com"},
                    {"subject_contains": ["invoice"]},
                ],
            },
            "newsletters": {
                "description": "Subscribed content",
                "rules": [{"header_list_unsubscribe": True}],
            },
        },
        "settings": {
            "llm_provider": "claude",
            "confidence_threshold": 0.7,
            "max_emails_per_run": 100,
            "suggestion_file": "suggestions.json",
        },
    }
    config_file = tmp_path / "labels.yaml"
    config_file.write_text(yaml.dump(config_data))

    config = load_config(config_file)

    assert "invoices" in config.labels
    assert config.labels["invoices"].description == "Bills and receipts"
    assert len(config.labels["invoices"].rules) == 2
    assert config.settings.llm_provider == "claude"
    assert config.settings.confidence_threshold == 0.7


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/labels.yaml"))


def test_label_definition_no_rules():
    label = LabelDefinition(description="LLM-only label", rules=[])
    assert label.rules == []
