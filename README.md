# Borrower Copilot

A self-assessment tool that helps an Indian borrower answer four questions
before they walk into a lender: should I borrow, how much, at what rate,
and what EMI should I agree to — plus a one-page Negotiation Card.

No login, no bureau pull, no data stored. Everything runs from what you
tell it, in your browser session only.

## Run it (under 5 minutes)

With [uv](https://docs.astral.sh/uv/) (recommended — no manual venv/pip step):

```bash
uv run streamlit run app.py
```

Or with plain pip:

```bash
pip install streamlit
streamlit run app.py
```

Opens at `http://localhost:8501`. Use the sidebar to load Priya, Ravi, or
Anita instantly, or fill in the form yourself.

## How it's built

```
app.py                 # Streamlit UI + wizard flow only — no domain logic here
rules/
    types.py            # Borrower, Range, DualView dataclasses
    eligibility.py       # O1: borrow / don't / borrow-less
    affordability.py     # O2: lender-vs-advocate dual reasoning, reconciled
    pricing.py            # O3: rate band + all-in APR
    emi.py                 # O4: EMI ceiling, tenure trade-off, stress test
    confidence.py         # range-widening based on how much was answered
questions/
    flow.py               # adaptive question list, filtered by income type
RULES.md                # every threshold and where it came from
```

`rules/` has zero Streamlit imports — it's pure Python, independently
testable, and it's the part meant to be defended and changed live in a
follow-up conversation. See `RULES.md` for the full reasoning behind every
number. The sidebar's "Assumptions panel" exposes the core FOIR thresholds
as live sliders for exactly that purpose.

## Design choice worth flagging

Instead of computing one number per output, the affordability engine (O2)
runs two competing positions — a conservative **Lender Model** and a
protective **Borrower Advocate** — and shows both before reconciling to
whichever is lower (the number that survives a bad month). This is meant
to make the core asymmetry in the brief ("the borrower has nothing, the
lender has a model") visible in the product itself, not just the copy.

## What's next / what I'd cut

**Next:** wire the co-applicant income through the same haircut logic used
for the primary applicant (currently added at face value); replace the
straight-line APR approximation with a proper IRR solve; add a persona
replay via URL params so a specific run-through can be shared as a link.

**Would cut if scoping tighter:** the tenure trade-off display (nice but
not scored as heavily as the core four outputs); the free-text "offers
received" field, which isn't parsed into the rate comparison yet — it's
collected but only surfaced as raw text.
