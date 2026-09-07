"""Adaptive question tree. Must questions are always asked. Additional
questions are filtered by income_type and purpose so a salaried IT
employee and a kirana owner never see the same list.
"""

MUST_QUESTIONS = [
    "purpose", "amount_wanted", "income_type", "net_monthly_income",
    "existing_emis", "household_expenses", "age", "city_tier", "credit_score",
]

# Additional questions: field_name -> (applies_to income_types, label, why_it_moves_a_number)
ADDITIONAL_QUESTIONS = {
    "income_history_years": (
        ["salaried", "self_employed"],
        "How many years in this job / business?",
        "Narrows the lender's trust discount on your income.",
    ),
    "variable_income_share": (
        ["self_employed", "informal"],
        "What share of your income is irregular month to month?",
        "Directly changes your safe-EMI buffer.",
    ),
    "existing_loan_detail": (
        ["self_employed", "informal", "salaried"],
        "Any details on existing loans (type, remaining tenure)?",
        "Refines the FOIR deduction beyond just the EMI total.",
    ),
    "card_utilisation": (
        ["salaried", "self_employed"],
        "What % of your credit card limit do you typically use?",
        "High utilisation nudges your rate band upward.",
    ),
    "bounced_payments_last_year": (
        ["salaried", "self_employed", "informal"],
        "Any bounced EMI or bill payments in the last year?",
        "Can trigger a 'don't borrow' verdict directly.",
    ),
    "emergency_savings_months": (
        ["salaried", "self_employed", "informal"],
        "How many months of expenses do you have in savings?",
        "Directly changes your stability buffer and safe EMI.",
    ),
    "collateral_value": (
        ["self_employed", "informal"],
        "Do you own property/land you could offer as collateral? Value?",
        "Can shift you from unsecured to secured pricing — several points lower rate.",
    ),
    "has_coapplicant": (
        ["salaried", "self_employed", "informal"],
        "Is there a co-applicant (spouse, family) with income?",
        "Adds to combined income used for affordability.",
    ),
    "coapplicant_income": (
        ["salaried", "self_employed", "informal"],
        "Co-applicant's net monthly income?",
        "Increases combined affordability directly.",
    ),
    "upcoming_large_expense": (
        ["salaried", "self_employed", "informal"],
        "Any large expense coming up (school fees, medical, festival)?",
        "Reduces the safe EMI ceiling for the stress test.",
    ),
    "loan_expected_return_monthly": (
        ["self_employed", "informal"],
        "If this loan is for business/productive use, what extra monthly income might it generate?",
        "Can raise the safe ceiling if the loan pays for itself.",
    ),
    "offers_received": (
        ["salaried", "self_employed", "informal"],
        "Any rate offers already received from a lender?",
        "Used directly in the Negotiation Card as a comparison point.",
    ),
    "regret_trigger": (
        ["salaried", "self_employed", "informal"],
        "What's the one thing that would make you regret taking this loan?",
        "Routes to a harder stress test if it signals income instability.",
    ),
}


def additional_questions_for(income_type: str) -> dict:
    return {
        k: v for k, v in ADDITIONAL_QUESTIONS.items()
        if income_type in v[0]
    }
