import fnmatch

from src.config import LabelDefinition, Rule
from src.models import EmailInput


def _match_rule(email: EmailInput, rule: Rule) -> bool:
    if rule.from_pattern is not None:
        if fnmatch.fnmatch(email.sender.lower(), rule.from_pattern.lower()):
            return True
    if rule.subject_contains is not None:
        subject_lower = email.subject.lower()
        for keyword in rule.subject_contains:
            if keyword.lower() in subject_lower:
                return True
    if rule.header_list_unsubscribe is True:
        # Cannot check headers from email preview alone; skip in rule matching.
        # This would need actual email headers passed in.
        pass
    return False


def match_rules(email: EmailInput, labels: dict[str, LabelDefinition]) -> list[str]:
    matched = []
    for label_name, label_def in labels.items():
        for rule in label_def.rules:
            if _match_rule(email, rule):
                matched.append(label_name)
                break
    return matched
