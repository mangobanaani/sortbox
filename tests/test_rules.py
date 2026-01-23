from src.classifier.rules import match_rules
from src.config import LabelDefinition, Rule
from src.models import EmailInput


def _make_email(**kwargs) -> EmailInput:
    defaults = {
        "email_id": "msg001",
        "sender": "test@example.com",
        "subject": "Test subject",
        "body_preview": "Test body",
    }
    defaults.update(kwargs)
    return EmailInput(**defaults)


def test_match_from_exact_domain():
    label = LabelDefinition(
        description="Invoices",
        rules=[Rule(**{"from": "*@stripe.com"})],
    )
    email = _make_email(sender="billing@stripe.com")
    assert match_rules(email, {"invoices": label}) == ["invoices"]


def test_match_from_wildcard_subdomain():
    label = LabelDefinition(
        description="Invoices",
        rules=[Rule(**{"from": "*@invoice.*"})],
    )
    email = _make_email(sender="noreply@invoice.mycompany.com")
    assert match_rules(email, {"invoices": label}) == ["invoices"]


def test_match_subject_contains():
    label = LabelDefinition(
        description="Invoices",
        rules=[Rule(subject_contains=["invoice", "receipt"])],
    )
    email = _make_email(subject="Your receipt for January")
    assert match_rules(email, {"invoices": label}) == ["invoices"]


def test_subject_contains_case_insensitive():
    label = LabelDefinition(
        description="Invoices",
        rules=[Rule(subject_contains=["Invoice"])],
    )
    email = _make_email(subject="INVOICE #1234")
    assert match_rules(email, {"invoices": label}) == ["invoices"]


def test_no_match_returns_empty():
    label = LabelDefinition(
        description="Invoices",
        rules=[Rule(**{"from": "*@stripe.com"})],
    )
    email = _make_email(sender="friend@gmail.com")
    assert match_rules(email, {"invoices": label}) == []


def test_multiple_labels_can_match():
    labels = {
        "invoices": LabelDefinition(
            description="Invoices",
            rules=[Rule(subject_contains=["invoice"])],
        ),
        "notifications": LabelDefinition(
            description="Notifications",
            rules=[Rule(**{"from": "*noreply@*"})],
        ),
    }
    email = _make_email(sender="noreply@billing.com", subject="Your invoice")
    result = match_rules(email, labels)
    assert "invoices" in result
    assert "notifications" in result


def test_label_with_no_rules_never_matches():
    label = LabelDefinition(description="LLM-only", rules=[])
    email = _make_email()
    assert match_rules(email, {"action-required": label}) == []


def test_noreply_wildcard():
    label = LabelDefinition(
        description="Notifications",
        rules=[Rule(**{"from": "*noreply@*"})],
    )
    email = _make_email(sender="noreply@github.com")
    assert match_rules(email, {"notifications": label}) == ["notifications"]
