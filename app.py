import streamlit as st
from rules.types import Borrower
from rules import affordability, pricing, emi, eligibility, confidence
from questions.flow import additional_questions_for

st.set_page_config(page_title="Borrower Copilot", page_icon="💳", layout="centered")

PERSONAS = {
    "— none —": None,
    "Priya (salaried, Bengaluru)": dict(
        name="Priya", age=29, city_tier="metro", income_type="salaried",
        net_monthly_income=110000, purpose="wedding", amount_wanted=800000,
        existing_emis=14000, household_expenses=28000, credit_score=780,
    ),
    "Ravi (self-employed, Mysuru)": dict(
        name="Ravi", age=42, city_tier="tier2", income_type="self_employed",
        net_monthly_income=35000, purpose="business", amount_wanted=1500000,
        existing_emis=0, household_expenses=20000, credit_score=None,
        collateral_value=4500000, income_history_years=14,
    ),
    "Anita (informal, Hubballi)": dict(
        name="Anita", age=35, city_tier="tier3_rural", income_type="informal",
        net_monthly_income=28000, purpose="vehicle", amount_wanted=150000,
        existing_emis=8000, household_expenses=18000, credit_score=None,
        bounced_payments_last_year=1, emergency_savings_months=0,
    ),
}

if "step" not in st.session_state:
    st.session_state.step = "form"
if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = False

st.title("💳 Borrower Copilot")
st.caption("Know what's fair before you walk into a lender.")

with st.sidebar:
    st.subheader("Demo personas")
    choice = st.selectbox("Load a persona", list(PERSONAS.keys()))
    if st.button("Load") and PERSONAS[choice]:
        st.session_state.persona_data = PERSONAS[choice]
        st.session_state.step = "form"
    st.divider()
    st.session_state.dev_mode = st.toggle("Assumptions panel (dev)", value=st.session_state.dev_mode)
    if st.session_state.dev_mode:
        st.caption("Edit thresholds live — recalculates instantly.")
        st.session_state.foir_salaried = st.slider("FOIR cap — salaried", 0.30, 0.60, 0.50, 0.01)
        st.session_state.foir_self = st.slider("FOIR cap — self-employed", 0.25, 0.55, 0.45, 0.01)
        st.session_state.foir_informal = st.slider("FOIR cap — informal", 0.20, 0.45, 0.35, 0.01)
        if st.button("Apply to engine"):
            affordability.FOIR_CAP["salaried"] = st.session_state.foir_salaried
            affordability.FOIR_CAP["self_employed"] = st.session_state.foir_self
            affordability.FOIR_CAP["informal"] = st.session_state.foir_informal
            st.success("Rules updated. Recalculate below.")

defaults = st.session_state.get("persona_data", {})

st.header("Tell us about the loan")
col1, col2 = st.columns(2)
with col1:
    purpose = st.selectbox("What's the loan for?", 
        ["wedding", "business", "vehicle", "home", "medical", "education", "consolidation", "other"],
        index=["wedding", "business", "vehicle", "home", "medical", "education", "consolidation", "other"].index(defaults.get("purpose", "wedding")))
    amount_wanted = st.number_input("Amount wanted (₹)", min_value=10000, value=int(defaults.get("amount_wanted", 500000)), step=10000)
with col2:
    income_type = st.selectbox("Income type", ["salaried", "self_employed", "informal"],
        index=["salaried", "self_employed", "informal"].index(defaults.get("income_type", "salaried")))
    net_monthly_income = st.number_input("Net monthly income (₹)", min_value=0, value=int(defaults.get("net_monthly_income", 50000)), step=1000)

st.header("Your finances")
col3, col4 = st.columns(2)
with col3:
    existing_emis = st.number_input("Existing EMIs / month (₹)", min_value=0, value=int(defaults.get("existing_emis", 0)), step=500)
    age = st.number_input("Age", min_value=18, max_value=75, value=int(defaults.get("age", 30)))
with col4:
    household_expenses = st.number_input("Household expenses / month (₹)", min_value=0, value=int(defaults.get("household_expenses", 15000)), step=500)
    city_tier = st.selectbox("City", ["metro", "tier2", "tier3_rural"],
        index=["metro", "tier2", "tier3_rural"].index(defaults.get("city_tier", "metro")))

credit_known = st.checkbox("I know my credit score", value=defaults.get("credit_score") is not None)
credit_score = None
if credit_known:
    credit_score = st.slider("Credit score", 300, 900, int(defaults.get("credit_score") or 700))
else:
    st.caption("That's fine — 'unknown' is modeled honestly, not treated as a bad score.")

st.header("A few more questions (optional — each one tightens your range)")
st.caption("Skip anything you don't know. More answers = narrower, more confident numbers.")

extra_answers = {}
relevant = additional_questions_for(income_type)
for field, (types, label, why) in relevant.items():
    with st.expander(f"{label}"):
        st.caption(f"Why we ask: {why}")
        if field in ("variable_income_share", "card_utilisation"):
            val = st.slider(label, 0.0, 1.0, float(defaults.get(field) or 0.0), key=field, label_visibility="collapsed")
            extra_answers[field] = val if val > 0 else None
        elif field == "bounced_payments_last_year":
            val = st.number_input(label, min_value=0, max_value=12, value=int(defaults.get(field) or 0), key=field, label_visibility="collapsed")
            extra_answers[field] = val
        elif field == "emergency_savings_months":
            val = st.number_input(label, min_value=0.0, max_value=36.0, value=float(defaults.get(field) or 0.0), step=0.5, key=field, label_visibility="collapsed")
            extra_answers[field] = val
        elif field == "collateral_value":
            val = st.number_input(label, min_value=0, value=int(defaults.get(field) or 0), step=10000, key=field, label_visibility="collapsed")
            extra_answers[field] = val if val > 0 else None
        elif field == "has_coapplicant":
            val = st.checkbox(label, value=bool(defaults.get(field, False)), key=field, label_visibility="collapsed")
            extra_answers[field] = val
        elif field == "coapplicant_income":
            val = st.number_input(label, min_value=0, value=int(defaults.get(field) or 0), step=1000, key=field, label_visibility="collapsed")
            extra_answers[field] = val if val > 0 else None
        elif field == "income_history_years":
            val = st.number_input(label, min_value=0.0, value=float(defaults.get(field) or 0.0), step=0.5, key=field, label_visibility="collapsed")
            extra_answers[field] = val if val > 0 else None
        elif field in ("upcoming_large_expense", "loan_expected_return_monthly"):
            val = st.number_input(label, min_value=0, value=int(defaults.get(field) or 0), step=1000, key=field, label_visibility="collapsed")
            extra_answers[field] = val if val > 0 else None
        elif field == "existing_loan_detail":
            val = st.text_input(label, value=defaults.get(field) or "", key=field, label_visibility="collapsed")
            extra_answers[field] = val or None
        elif field == "regret_trigger":
            val = st.text_input(label, value=defaults.get(field) or "", key=field, label_visibility="collapsed")
            extra_answers[field] = val or None
        elif field == "offers_received":
            val = st.text_input("Lender name and rate, comma-separated", key=field, label_visibility="collapsed")
            extra_answers[field] = [v.strip() for v in val.split(",")] if val else []

run = st.button("Get my numbers", type="primary", use_container_width=True)

if run:
    b = Borrower(
        name=defaults.get("name", "You"), age=age, city_tier=city_tier, income_type=income_type,
        net_monthly_income=net_monthly_income, purpose=purpose, amount_wanted=amount_wanted,
        existing_emis=existing_emis, household_expenses=household_expenses, credit_score=credit_score,
        **{k: v for k, v in extra_answers.items() if k in Borrower.__dataclass_fields__},
    )

    conf = confidence.score(b)
    aff = affordability.compute(b)
    rate = pricing.rate_band(b)
    emi_result = emi.compute(b, aff.reconciled, rate["rate_low"], rate["rate_high"])
    verdict = eligibility.assess(b, aff.reconciled)

    st.divider()
    st.header(f"Results for {b.name}")

    verdict_color = {"borrow": "green", "borrow_less": "orange", "dont_borrow": "red"}[verdict.verdict]
    st.markdown(f"### :{verdict_color}[{verdict.headline}]")
    st.write(verdict.reason)
    if verdict.red_flags:
        st.warning(" · ".join(verdict.red_flags))

    st.subheader("O2 — How much")
    c1, c2 = st.columns(2)
    c1.metric("Lender will likely sanction", f"₹{aff.lender_position:,.0f}")
    c2.metric("You can safely carry", f"₹{aff.advocate_position:,.0f}")
    st.info(f"**Use: ₹{aff.reconciled:,.0f}.** {aff.reconciled_reason}")
    with st.expander("See both sides argue this out"):
        st.markdown(f"**🏦 Lender's position — ₹{aff.lender_position:,.0f}**")
        st.caption(aff.lender_reason)
        st.markdown(f"**🧑 Advocate's position — ₹{aff.advocate_position:,.0f}**")
        st.caption(aff.advocate_reason)

    st.subheader("O3 — Fair rate")
    st.write(f"**{rate['rate_low']}% – {rate['rate_high']}%** (confidence: {conf['level']})")
    st.write(f"All-in APR including fees: **{rate['apr_low']}% – {rate['apr_high']}%**")
    st.caption(rate["basis"])

    st.subheader("O4 — EMI to agree to")
    if emi_result["amount_used"] <= 0:
        st.warning("No EMI ceiling to show — your safe borrowing amount is ₹0 right now. See O1: fix the underlying issue before an EMI number is meaningful.")
    else:
        st.metric("Monthly ceiling", f"₹{emi_result['emi_ceiling']:,.0f}",
                   help=f"Over {emi_result['tenure_years']} years on ₹{emi_result['amount_used']:,.0f}")
        st.caption(emi_result["basis"])
        tc1, tc2 = st.columns(2)
        tc1.write(f"Shorter term ({emi_result['tenure_short_years']}y): ₹{emi_result['tenure_short_emi']:,.0f}/mo")
        tc2.write(f"Longer term ({emi_result['tenure_long_years']}y): ₹{emi_result['tenure_long_emi']:,.0f}/mo")

        stress = emi_result["stress"]
        if stress["survives_income_shock"]:
            st.success(f"Stress test: survives a {stress['income_drop_pct']}% income drop (₹{stress['surplus_after_income_drop']:,.0f}/mo left over).")
        else:
            st.error(f"Stress test: a {stress['income_drop_pct']}% income drop leaves you ₹{abs(stress['surplus_after_income_drop']):,.0f} short/month.")
        st.caption(f"If rates rise {stress['rate_rise_pp']}pp: EMI becomes ₹{stress['emi_if_rate_rises']:,.0f} (+₹{stress['extra_monthly_if_rate_rises']:,.0f}/mo).")

    st.divider()
    st.subheader("📋 Negotiation Card")
    with st.container(border=True):
        st.markdown(f"**{b.name}** · {b.income_type.replace('_',' ')} · {b.city_tier}")
        st.markdown(f"Fair rate for your profile: **{rate['rate_low']}%–{rate['rate_high']}%** (all-in APR {rate['apr_low']}%–{rate['apr_high']}%)")
        st.markdown(f"Amount to ask for: **₹{aff.reconciled:,.0f}**")
        st.markdown(f"EMI you should hold to: **₹{emi_result['emi_ceiling']:,.0f}/month** over {emi_result['tenure_years']} years")
        st.markdown(f"_Confidence: {conf['level']} — based on {conf['answered_fraction']:.0%} of tightening questions answered._")
        if conf["missing_that_would_help"]:
            st.caption("Answering more would narrow this: " + ", ".join(conf["missing_that_would_help"][:3]))

    st.caption("This is a self-assessment, not a bureau-verified offer. No data was stored — refresh to clear.")
