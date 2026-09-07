"""O3 — Fair interest rate band and all-in APR.

Base rate bands are indicative market ranges by loan product (documented in
RULES.md as "my judgement, anchored to publicly advertised bank/NBFC rate
cards as of 2026" — not a live feed). We adjust off a base band using
credit score, income type, and collateral.
"""

from .types import Borrower

# Base annual rate bands by loan type: (low, high), before adjustments.
BASE_BAND = {
    "home": (8.5, 10.5),
    "vehicle": (9.0, 13.0),
    "business": (11.0, 16.0),       # LAP / secured business
    "gold": (9.5, 13.0),
    "personal": (11.0, 22.0),
    "consolidation": (11.0, 22.0),
    "medical": (11.0, 22.0),
    "wedding": (11.0, 22.0),
    "education": (9.5, 13.0),
    "other": (11.0, 22.0),
}

PROCESSING_FEE_PCT = {
    "home": 0.005,
    "vehicle": 0.01,
    "business": 0.015,
    "gold": 0.005,
    "personal": 0.02,
    "consolidation": 0.02,
    "medical": 0.02,
    "wedding": 0.02,
    "education": 0.01,
    "other": 0.02,
}


def _score_adjustment(score: int) -> float:
    """Percentage points added/subtracted from the base band midpoint logic."""
    if score >= 780:
        return -1.5
    if score >= 720:
        return -0.5
    if score >= 650:
        return 0.5
    if score >= 550:
        return 2.5
    return 4.0  # sub-550 or effectively no formal history


def indicative_rate_for(b: Borrower, score: int) -> dict:
    lo, hi = BASE_BAND[b.purpose]
    adj = _score_adjustment(score)

    # informal/self-employed with no collateral pushes toward the top of the band
    income_penalty = 0.0
    if b.income_type == "informal":
        income_penalty = 2.0
    elif b.income_type == "self_employed" and not (b.collateral_value and b.collateral_value > 0):
        income_penalty = 1.0

    # collateral pulls an otherwise-unsecured ask toward secured pricing
    collateral_discount = 0.0
    if b.collateral_value and b.collateral_value >= b.amount_wanted * 1.5:
        collateral_discount = 3.0

    low_case_rate = max(lo, lo + adj - collateral_discount)
    high_case_rate = hi + income_penalty - collateral_discount
    high_case_rate = max(low_case_rate + 0.5, high_case_rate)

    return {
        "low_case_rate": round(low_case_rate, 2),
        "high_case_rate": round(high_case_rate, 2),
    }


def apr_all_in(rate_pct: float, amount: float, tenure_years: float, purpose: str) -> float:
    """Approximate all-in APR folding in processing fee, spread over the loan term.
    Simplification documented in RULES.md: fee amortized straight-line over tenure
    rather than solved via IRR — stated explicitly as an approximation."""
    fee_pct = PROCESSING_FEE_PCT[purpose]
    fee_amount = amount * fee_pct
    annualised_fee_impact = (fee_amount / amount) / max(tenure_years, 0.5) * 100
    return round(rate_pct + annualised_fee_impact, 2)


def rate_band(b: Borrower) -> dict:
    score = b.credit_score if b.credit_score is not None else 650
    confidence = "medium" if b.credit_score is not None else "low"
    r = indicative_rate_for(b, score)
    tenure_years = 5 if b.purpose in ("wedding", "medical", "consolidation", "other") else 7
    apr_low = apr_all_in(r["low_case_rate"], b.amount_wanted, tenure_years, b.purpose)
    apr_high = apr_all_in(r["high_case_rate"], b.amount_wanted, tenure_years, b.purpose)

    basis = (
        f"Base {b.purpose} band is {BASE_BAND[b.purpose][0]}-{BASE_BAND[b.purpose][1]}%, adjusted for "
        f"{'a known' if b.credit_score is not None else 'an unknown (assumed 650, mid-range)'} credit "
        f"score and {b.income_type.replace('_', ' ')} income."
        + (" Collateral value discounts this toward secured-loan pricing."
           if b.collateral_value and b.collateral_value >= b.amount_wanted * 1.5 else "")
    )

    return {
        "rate_low": r["low_case_rate"],
        "rate_high": r["high_case_rate"],
        "apr_low": apr_low,
        "apr_high": apr_high,
        "confidence": confidence,
        "basis": basis,
    }
