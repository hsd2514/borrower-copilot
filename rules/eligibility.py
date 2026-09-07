"""O1 — Borrow / Don't borrow / Borrow less.

This runs LAST in the pipeline conceptually (it needs affordability output)
but is scored as its own output. Kept here as a pure function of the
borrower plus the affordability result so it stays testable in isolation.
"""

from dataclasses import dataclass
from typing import Literal
from .types import Borrower

Verdict = Literal["borrow", "borrow_less", "dont_borrow"]


@dataclass
class EligibilityResult:
    verdict: Verdict
    headline: str
    reason: str
    red_flags: list


def assess(b: Borrower, safe_max: float) -> EligibilityResult:
    red_flags = []

    # Hard stop conditions — these override everything else.
    if b.bounced_payments_last_year and b.bounced_payments_last_year >= 1:
        red_flags.append(f"{b.bounced_payments_last_year} bounced payment(s) in the last year")
    if b.income_type == "informal" and (b.emergency_savings_months or 0) < 1 and b.existing_emis > 0:
        red_flags.append("no savings buffer while already carrying debt on informal income")

    existing_debt_load = b.existing_emis / b.net_monthly_income if b.net_monthly_income else 1

    # DON'T BORROW: current debt is already unsustainable, or a hard red flag on thin income.
    if existing_debt_load > 0.5 and b.income_type != "salaried":
        red_flags.append(f"existing EMIs already consume {existing_debt_load:.0%} of stated income")

    if red_flags and (b.bounced_payments_last_year or 0) >= 1 and b.income_type != "salaried":
        return EligibilityResult(
            verdict="dont_borrow",
            headline="Don't borrow — not yet",
            reason=(
                "A bounced payment plus " + red_flags[-1] if len(red_flags) > 1 else red_flags[0]
            ) + ". Fix the existing debt first; a new loan on top of a bounce will likely be priced "
                "punitively or refused, and either way it makes the underlying problem worse.",
            red_flags=red_flags,
        )

    if existing_debt_load > 0.6:
        return EligibilityResult(
            verdict="dont_borrow",
            headline="Don't borrow — existing debt is already at the limit",
            reason=f"Existing EMIs already take {existing_debt_load:.0%} of stated monthly income. "
                    "Any lender's own affordability check would decline this, and taking on more "
                    "would mean cutting essential household spending.",
            red_flags=red_flags,
        )

    # BORROW LESS: what they want exceeds what's safe by a wide margin.
    if b.amount_wanted > safe_max * 1.15:
        shortfall_pct = (1 - safe_max / b.amount_wanted) * 100
        return EligibilityResult(
            verdict="borrow_less",
            headline=f"Borrow less — ask for closer to your safe ceiling",
            reason=f"You're asking for {shortfall_pct:.0f}% more than what you can safely carry "
                    f"at a sustainable EMI. Borrowing the full amount would either stretch your "
                    f"monthly outflow past a safe limit or force a longer tenure at higher total cost.",
            red_flags=red_flags,
        )

    return EligibilityResult(
        verdict="borrow",
        headline="You can reasonably borrow this",
        reason="Requested amount is within what your income and existing obligations can safely support.",
        red_flags=red_flags,
    )
