"""O4 — EMI ceiling to agree to, tenure trade-off, and a stress case."""

from .types import Borrower


def emi_for_amount(principal: float, annual_rate_pct: float, tenure_years: float) -> float:
    """Standard reducing-balance EMI formula."""
    if principal <= 0:
        return 0.0
    r = annual_rate_pct / 12 / 100
    n = tenure_years * 12
    if r == 0:
        return principal / n
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return emi


def amount_for_emi(emi: float, annual_rate_pct: float, tenure_years: float) -> float:
    """Inverse: how much principal a given EMI capacity supports."""
    if emi <= 0:
        return 0.0
    r = annual_rate_pct / 12 / 100
    n = tenure_years * 12
    if r == 0:
        return emi * n
    principal = emi * ((1 + r) ** n - 1) / (r * (1 + r) ** n)
    return principal


def max_emi_for_amount_and_rate(principal: float, annual_rate_pct: float, tenure_years: float) -> float:
    return emi_for_amount(principal, annual_rate_pct, tenure_years)


def stress_test(b: Borrower, emi: float) -> dict:
    """One stress case: income drops 20% (job loss / bad season) or rate rises 2pp."""
    income_drop_income = b.net_monthly_income * 0.80
    surplus_after_drop = income_drop_income - b.household_expenses - b.existing_emis - emi
    survives_income_shock = surplus_after_drop >= 0

    return {
        "income_drop_pct": 20,
        "surplus_after_income_drop": round(surplus_after_drop),
        "survives_income_shock": survives_income_shock,
        "rate_rise_pp": 2,
    }


def compute(b: Borrower, safe_amount: float, rate_low: float, rate_high: float) -> dict:
    tenure_years = 5 if b.purpose in ("wedding", "medical", "consolidation", "other") else 7
    # If the safe ceiling is 0 (a "don't borrow" case), don't fall back to the
    # full requested amount — that would silently produce a fake EMI number
    # for someone who shouldn't be borrowing at all.
    amount = min(b.amount_wanted, safe_amount)

    emi_at_low_rate = emi_for_amount(amount, rate_low, tenure_years)
    emi_at_high_rate = emi_for_amount(amount, rate_high, tenure_years)

    # tenure trade-off: same amount, shorter vs longer term
    short_tenure = max(2, tenure_years - 2)
    long_tenure = tenure_years + 3
    emi_short = emi_for_amount(amount, rate_high, short_tenure)
    emi_long = emi_for_amount(amount, rate_high, long_tenure)

    ceiling_emi = emi_at_high_rate  # agree to the conservative (higher-rate) EMI, not the optimistic one
    stress = stress_test(b, ceiling_emi)

    rate_rise_emi = emi_for_amount(amount, rate_high + 2, tenure_years)
    stress["emi_if_rate_rises"] = round(rate_rise_emi)
    stress["extra_monthly_if_rate_rises"] = round(rate_rise_emi - ceiling_emi)

    basis = (
        f"Ceiling uses the higher end of your rate band ({rate_high}%) over {tenure_years} years on the "
        f"amount you should actually borrow (₹{amount:,.0f}), not the full ask — so the number won't "
        f"break if your quote comes in worse than the optimistic case."
    )

    return {
        "amount_used": round(amount),
        "tenure_years": tenure_years,
        "emi_ceiling": round(ceiling_emi),
        "emi_optimistic": round(emi_at_low_rate),
        "tenure_short_years": short_tenure,
        "tenure_short_emi": round(emi_short),
        "tenure_long_years": long_tenure,
        "tenure_long_emi": round(emi_long),
        "stress": stress,
        "basis": basis,
    }
