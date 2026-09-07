"""Shared data types. No UI imports here — this file stays pure."""

from dataclasses import dataclass, field
from typing import Optional, Literal

IncomeType = Literal["salaried", "self_employed", "informal"]
LoanPurpose = Literal["wedding", "business", "vehicle", "home", "medical", "education", "consolidation", "other"]


@dataclass
class Borrower:
    # --- Must questions ---
    name: str
    age: int
    city_tier: Literal["metro", "tier2", "tier3_rural"]
    income_type: IncomeType
    net_monthly_income: float          # what they tell you; for self-employed/informal this may be an estimate
    purpose: LoanPurpose
    amount_wanted: float
    existing_emis: float = 0.0
    household_expenses: float = 0.0
    credit_score: Optional[int] = None  # None = unknown, never treated as 0/300

    # --- Additional questions (all Optional — silence widens bands, never narrows) ---
    income_history_years: Optional[float] = None
    variable_income_share: Optional[float] = None       # 0-1, fraction of income that's irregular
    existing_loan_detail: Optional[str] = None
    card_utilisation: Optional[float] = None             # 0-1
    bounced_payments_last_year: Optional[int] = None
    emergency_savings_months: Optional[float] = None
    collateral_value: Optional[float] = None
    has_coapplicant: bool = False
    coapplicant_income: Optional[float] = None
    upcoming_large_expense: Optional[float] = None
    loan_expected_return_monthly: Optional[float] = None  # if productive-use loan
    offers_received: list = field(default_factory=list)   # [(lender, rate)]
    regret_trigger: Optional[str] = None                  # free text: "what would make you regret this"


@dataclass
class Range:
    low: float
    high: float
    confidence: Literal["low", "medium", "high"]
    basis: str  # one-sentence why

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2


@dataclass
class DualView:
    """Two competing positions on the same question, reconciled into one verdict."""
    lender_position: float
    lender_reason: str
    advocate_position: float
    advocate_reason: str
    reconciled: float
    reconciled_reason: str
