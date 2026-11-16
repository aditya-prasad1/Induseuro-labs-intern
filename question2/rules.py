from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from shared.kb import article_ids


class Action(str, Enum):
    REFUND = "REFUND"
    REPLACE = "REPLACE"
    SEND_ARTICLE = "SEND_ARTICLE"
    ESCALATE_TIER2 = "ESCALATE_TIER2"


@dataclass(frozen=True)
class RuleResult:
    action: Action
    kb_article: str


# These are the only policy constants. Each key must be a data/kb article slug.
KB_RULES = {
    "subscription-cooling-off": {
        "refund_cutoff_days": 30,
    },
    "returns-within-30-days": {"refund_cutoff_days": 30},
    "digital-license-no-refund": {"license_revealed": True},
    "damage-replacement-7-days": {"replacement_cutoff_days": 7},
    "custom-items-no-replace": {"customized_damage_escalates": True},
}


def _article(slug: str) -> str:
    """Return a policy article slug and reject rules without a KB source."""
    if slug not in article_ids():
        raise RuntimeError(f"Rule has no matching KB article: {slug}")
    return slug


def resolve_order(order: dict) -> RuleResult:
    """Apply the boundary conditions documented by the KB articles."""
    product_type = order.get("product_type")

    if product_type == "subscription":
        age = int(order.get("subscription_age_days", 0))
        article = "subscription-cooling-off"
        if age <= KB_RULES[article]["refund_cutoff_days"]:
            return RuleResult(Action.REFUND, _article(article))
        return RuleResult(Action.SEND_ARTICLE, _article(article))

    if (
        KB_RULES["digital-license-no-refund"]["license_revealed"]
        and order.get("license_revealed")
    ):
        return RuleResult(Action.SEND_ARTICLE, _article("digital-license-no-refund"))

    if (
        KB_RULES["custom-items-no-replace"]["customized_damage_escalates"]
        and order.get("customized")
        and order.get("damage_reported")
    ):
        return RuleResult(Action.ESCALATE_TIER2, _article("custom-items-no-replace"))

    if order.get("damage_reported") and not order.get("customized"):
        if (
            int(order.get("delivered_days_ago", 99))
            <= KB_RULES["damage-replacement-7-days"]["replacement_cutoff_days"]
        ):
            return RuleResult(Action.REPLACE, _article("damage-replacement-7-days"))

    if product_type == "physical" and not order.get("opened"):
        if (
            int(order.get("delivered_days_ago", 99))
            <= KB_RULES["returns-within-30-days"]["refund_cutoff_days"]
        ):
            return RuleResult(Action.REFUND, _article("returns-within-30-days"))

    return RuleResult(Action.ESCALATE_TIER2, _article("returns-within-30-days"))
