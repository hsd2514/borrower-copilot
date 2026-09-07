"""O2 — Maximum amount: lender-will-sanction vs borrower-can-safely-carry.

The dual-voice pattern: a Lender Model (FOIR-strict, penalizes informal/
variable income, ignores lived reality) argues against a Borrower Advocate
(protects the person, weighs savings buffer and real cash flow). We show
both, and reconcile explicitly rather than silently picking one.
"""

from dataclasses import dataclass
from .types import Borrower, DualView
from .pricing import indicative_rate_for
from .emi import max_emi_for_amount_and_rate, amount_for_emi


# FOIR (Fixed Obligation to Income Ratio) caps — RBI-style convention, not law.
FOIR_CAP = {
    "salaried": 0.50,
    "self_employed": 0.45,
    "informal": 0.35,
}

# How much the lender discounts stated income when it's undocumented / irregular.
INCOME_HAIRCUT = {
    "salaried": 0.0,
    "self_employed": 0.20,   # ITR often understates cash income; lender only trusts the filed figure
    "informal": 0.35,
}


def _lender_view(b: Borrower) -> tuple[float, str]:
    """Conservative: strict FOIR on haircut income, ignores savings buffer."""
    haircut = INCOME_HAIRCUT[b.income_type]
    trusted_income = b.net_monthly_income * (1 - haircut)
    cap = FOIR_CAP[b.income_type]
    available_emi = max(0.0, trusted_income * cap - b.existing_emis)

    # unknown credit score → lender assumes below-average, not neutral
    score = b.credit_score if b.credit_score is not None else 650
    rate = indicative_rate_for(b, score)["low_case_rate"]  # lender quotes their better rate to sound generous
    tenure_years = 5 if b.purpose in ("wedding", "medical", "consolidation", "other") else 7
    sanction = amount_for_emi(available_emi, rate, tenure_years)

    reason = (
        f"Trusts {int((1-haircut)*100)}% of stated income (₹{trusted_income:,.0f}), caps obligations at "
        f"{cap:.0%} FOIR, subtracts existing EMI of ₹{b.existing_emis:,.0f}, assumes a "
        f"{'known' if b.credit_score is not None else 'below-average (650, since unknown)'} credit score."
    )
    return sanction, reason


def _advocate_view(b: Borrower) -> tuple[float, str]:
    """Protective: uses real cash flow after living expenses and buffer, not just a ratio."""
    monthly_surplus = b.net_monthly_income - b.household_expenses - b.existing_emis
    # keep a buffer proportional to income stability
    stability_buffer = 0.15
    if b.income_type != "salaried":
        stability_buffer = 0.30
    if b.variable_income_share and b.variable_income_share > 0.4:
        stability_buffer += 0.10
    if (b.emergency_savings_months or 0) >= 3:
        stability_buffer -= 0.05  # they can absorb a bad month, be slightly less conservative

    safe_emi = max(0.0, monthly_surplus * (1 - stability_buffer))
    score = b.credit_score if b.credit_score is not None else 650
    rate = indicative_rate_for(b, score)["high_case_rate"]  # advocate assumes the worse rate, to be safe
    tenure_years = 5 if b.purpose in ("wedding", "medical", "consolidation", "other") else 7
    safe_amount = amount_for_emi(safe_emi, rate, tenure_years)

    reason = (
        f"Starts from real leftover cash (income − living costs ₹{b.household_expenses:,.0f} − existing "
        f"EMI ₹{b.existing_emis:,.0f} = ₹{monthly_surplus:,.0f}/month), keeps back a "
        f"{stability_buffer:.0%} buffer for income shocks, and prices at the higher end of your likely "
        f"rate so the number doesn't collapse if the quote comes in worse than expected."
    )
    return safe_amount, reason


def compute(b: Borrower) -> DualView:
    lender_amt, lender_reason = _lender_view(b)
    advocate_amt, advocate_reason = _advocate_view(b)

    # Reconciliation: the borrower should use whichever is LOWER — that's the one
    # that won't break them, even if a lender would offer more.
    reconciled = min(lender_amt, advocate_amt)
    if reconciled == advocate_amt and advocate_amt < lender_amt:
        recon_reason = (
            "Use the lower, borrower-safe number. A lender may sanction more, but sanctioning "
            "isn't the same as affording — this is the ceiling that survives a bad month."
        )
    else:
        recon_reason = (
            "Your safe cash flow actually supports more than a lender's own FOIR rule would sanction — "
            "the lender's number is the binding constraint here, not your budget."
        )

    return DualView(
        lender_position=round(lender_amt, -3),
        lender_reason=lender_reason,
        advocate_position=round(advocate_amt, -3),
        advocate_reason=advocate_reason,
        reconciled=round(reconciled, -3),
        reconciled_reason=recon_reason,
    )
