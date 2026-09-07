"""Confidence widens with silence. Never narrows a range with no basis.

Confidence is computed from how many of the 'additional' questions were
actually answered, weighted by how much each one matters for this
borrower's income type (e.g. variable_income_share matters a lot for
self-employed, not at all for salaried).
"""

from .types import Borrower

# Which additional fields matter for which income type, and their weight.
RELEVANT_FIELDS = {
    "salaried": {
        "income_history_years": 0.15,
        "card_utilisation": 0.15,
        "bounced_payments_last_year": 0.20,
        "emergency_savings_months": 0.20,
        "upcoming_large_expense": 0.15,
        "offers_received": 0.15,
    },
    "self_employed": {
        "income_history_years": 0.20,
        "variable_income_share": 0.20,
        "existing_loan_detail": 0.10,
        "emergency_savings_months": 0.20,
        "collateral_value": 0.15,
        "loan_expected_return_monthly": 0.15,
    },
    "informal": {
        "variable_income_share": 0.20,
        "bounced_payments_last_year": 0.25,
        "emergency_savings_months": 0.25,
        "has_coapplicant": 0.10,
        "loan_expected_return_monthly": 0.20,
    },
}


def score(b: Borrower) -> dict:
    fields = RELEVANT_FIELDS[b.income_type]
    answered_weight = 0.0
    missing = []

    for field_name, weight in fields.items():
        val = getattr(b, field_name, None)
        is_answered = val is not None and val != [] and val is not False
        if is_answered:
            answered_weight += weight
        else:
            missing.append(field_name)

    # credit score known/unknown also matters
    if b.credit_score is not None:
        answered_weight += 0.10
    else:
        missing.append("credit_score")

    answered_weight = min(answered_weight, 1.0)

    if answered_weight >= 0.65:
        level = "high"
    elif answered_weight >= 0.35:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "answered_fraction": round(answered_weight, 2),
        "missing_that_would_help": missing,
    }


def widen_band(low: float, high: float, level: str) -> tuple:
    """Widen a computed band based on confidence — never narrow beyond the base calc."""
    mid = (low + high) / 2
    span = high - low
    if level == "low":
        widened_span = span * 1.6
    elif level == "medium":
        widened_span = span * 1.2
    else:
        widened_span = span
    return round(mid - widened_span / 2, 2), round(mid + widened_span / 2, 2)
