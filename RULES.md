# RULES.md

Every threshold, band, and assumption the app uses, why, and where it came from.
Read this alongside `/rules/*.py` — the code is the source of truth; this is the
explanation of intent.

## Design principle: dual-voice reconciliation

For O2 (amount) and O3 (rate), the engine computes **two competing positions**
before settling on one number:

- **Lender Model** — conservative, trusts less of your stated income if it's
  undocumented, applies a strict FOIR ratio, assumes a below-average credit
  score if unknown.
- **Borrower Advocate** — starts from real leftover cash flow after living
  expenses, keeps a stability buffer sized to income volatility, and prices
  at the *worse* end of the likely rate band so the number doesn't collapse
  if the actual quote is worse than hoped.

We show both, then reconcile to the **lower** of the two — the number that
survives a bad month, even if a lender would technically offer more. This is
documented per-output below.

## O1 — Borrow / Don't borrow / Borrow less

| What | Value | Why / Source |
|---|---|---|
| Don't-borrow trigger: bounce + high debt load | ≥1 bounced payment in last year AND non-salaried | My judgement — a bounce is the strongest observable signal of current distress; a new loan on top of one usually gets priced punitively or worsens the problem. |
| Don't-borrow trigger: existing debt load | Existing EMI > 60% of stated income | My judgement, anchored loosely to RBI's informal guidance that most lenders decline above ~50-60% total obligation ratio. |
| Borrow-less trigger | Amount wanted > 115% of safe ceiling | My judgement — a 15% buffer distinguishes "slightly ambitious ask" from "meaningfully overreaching," avoiding false positives on borderline cases. |

## O2 — Maximum amount (FOIR-based)

| What | Value | Why / Source |
|---|---|---|
| FOIR cap — salaried | 50% | Common Indian lender convention (FOIR / obligation-to-income ratio), publicly cited by multiple bank underwriting policies. |
| FOIR cap — self-employed | 45% | My judgement — self-employed income is less predictable, lenders typically shade this down 5pp from salaried. |
| FOIR cap — informal | 35% | My judgement — no documentation to verify income, so the safety margin is largest here. |
| Income haircut — self-employed | 20% | My judgement — ITR-filed income commonly understates real cash flow (for tax reasons), but a lender can only underwrite the documented figure. |
| Income haircut — informal | 35% | My judgement — no formal documentation at all; largest discount. |
| Unknown credit score (lender view) | Treated as 650 | Explicit design choice per brief rule 3 ("unknown is never zero") — 650 is roughly the boundary between prime and subprime in CIBIL's public banding, used as a deliberately neutral-to-cautious placeholder, never a floor score. |
| Advocate stability buffer | 15% (salaried) / 30% (non-salaried), +10% if variable income share > 40%, −5% if emergency savings ≥ 3 months | My judgement — buffer scales with income unpredictability and offsets by existing safety net. |
| Reconciliation | min(lender, advocate) | Documented above — the ceiling that survives a bad month, not the higher of the two. |

## O3 — Fair rate and APR

| What | Value | Why / Source |
|---|---|---|
| Base rate bands by product | Home 8.5–10.5%, Vehicle 9–13%, Business/LAP 11–16%, Gold 9.5–13%, Personal/wedding/medical/consolidation 11–22%, Education 9.5–13% | My judgement, anchored to publicly advertised bank/NBFC rate cards as of 2026. Not a live feed — documented as approximate, not authoritative. |
| Credit score adjustment | ≥780: −1.5pp · ≥720: −0.5pp · ≥650: +0.5pp · ≥550: +2.5pp · <550: +4pp | My judgement, modeling CIBIL's rough public score tiers (750+ "excellent" down to sub-600 "poor"). |
| Income-type penalty | Informal: +2pp · Self-employed w/o collateral: +1pp | My judgement — reflects real-world pricing gap for undocumented income. |
| Collateral discount | −3pp if collateral value ≥ 1.5× amount wanted | My judgement — meaningfully over-collateralized asks should price close to secured-loan rates. |
| Processing fee, by product | 0.5%–2% | My judgement, anchored to typically advertised bank/NBFC processing fee ranges. |
| APR calculation | Rate + (fee ÷ amount ÷ tenure) | **Approximation, explicitly not IRR-solved.** Straight-line amortization of the fee over tenure years, added to nominal rate. A true APR would solve for the effective rate given fee-adjusted disbursal; we simplify and say so here rather than pretend precision we don't have. |

## O4 — EMI ceiling and stress test

| What | Value | Why / Source |
|---|---|---|
| EMI formula | Standard reducing-balance amortization | Standard financial formula, not an assumption. |
| Ceiling uses which rate | High end of the rate band | My judgement — agree to an EMI that still works if your actual quote is the pessimistic case, not the best case. |
| Tenure — short-term purposes | 5 years (wedding, medical, consolidation, other) | My judgement — these purposes don't typically justify long amortization. |
| Tenure — asset/business purposes | 7 years (business, vehicle, home, gold, education) | My judgement — matches typical asset-backed or productive-use tenures. |
| Stress case 1 | Income drops 20% | My judgement — a round, conservative shock large enough to be meaningful (job loss, bad season) without being an extreme tail event. |
| Stress case 2 | Rate rises 2pp | My judgement — a realistic single-cycle rate-hike scenario, not a crisis scenario. |
| Tenure trade-off shown | −2 years / +3 years from base tenure | My judgement — gives the borrower a visible sense of the EMI-vs-tenure lever without overwhelming with every possible tenure. |

## Confidence (range-widening logic)

| What | Value | Why / Source |
|---|---|---|
| Field relevance weights | Different per income type (see `rules/confidence.py`) | My judgement — e.g. `variable_income_share` matters heavily for self-employed/informal, not at all for salaried; weights sum to ~1.0 per income type plus a 0.10 credit-score component. |
| Confidence bands | High ≥65% answered-weight · Medium ≥35% · Low below | My judgement — round thresholds chosen so the "must questions only" case always lands in Low, matching the brief's requirement that minimal answers produce wide, low-confidence ranges. |
| Rule applied | Never narrow a computed range below what the base calculation gives — only widen | Direct implementation of brief rule 2 ("confidence widens with silence, never narrows"). |

## What we explicitly do NOT know / are guessing on

- Real-time bank/NBFC rate cards — bands are static judgement calls, not a live feed. Documented above per product.
- True IRR-based APR — we use a straight-line fee approximation, stated explicitly in the O3 table.
- CIBIL score-to-rate mapping is not publicly precise; our tiering is a reasonable approximation, not the actual bureau-lender pricing formula.
- We do not model regional/city-tier cost-of-living differences in `household_expenses` — the borrower states their actual number, so this is self-correcting, but we don't sanity-check it against city tier.
- Co-applicant income is added at face value with no separate haircut — a simplification; a more complete model would apply the same income-type haircut logic to the co-applicant.
