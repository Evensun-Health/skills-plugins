<scope>
The risk score is just one input. The actual money that moves between issuers is the **risk transfer** — a per-member-per-month dollar amount computed at the plan level, settled annually, that redistributes premium from issuers with low-risk populations to issuers with high-risk populations within the same state and market (individual or small-group).

This reference covers the full transfer formula, the role of each component, and why metal-level optimization for high-risk populations is a real lever beyond just maximizing the risk score.
</scope>

<transfer_formula>
The CMS-published transfer formula for plan `i` in state `s` (per billable member month):

```
T(i) = [   PLRS_i · IDF_i · GCF_i                AV_i · ARF_i · IDF_i · GCF_i        ]
       [  ─────────────────────────────────  -  ───────────────────────────────────  ] · P̄_s
       [  Σ(s_i · PLRS_i · IDF_i · GCF_i)        Σ(s_i · AV_i · ARF_i · IDF_i · GCF_i) ]
```

Multiplied by the plan's billable member months to get the dollar transfer.

**Plan-specific factors (subscript i):**
- `PLRS_i` — Plan Liability Risk Score. The enrollee-month-weighted average risk score for the plan. **This is what the HHS-HCC model produces.**
- `IDF_i` — Induced Demand Factor. Premium-set adjustment for utilization induced by lower cost-sharing (Platinum induces more use than Bronze).
- `GCF_i` — Geographic Calibration Factor. Adjusts for cost differences across rating areas.
- `AV_i` — Actuarial Value. The plan's metal-level AV.
- `ARF_i` — Allowable Rating Factor. The enrollee-month-weighted average of the ACA federal age curve (or state-approved alternative) applied to the plan's enrollment.
- `s_i` — the plan's share of statewide market enrollment (for the same market — individual or small-group).

**Statewide constants (subscript s):**
- `P̄_s` — Statewide average premium for the same market.
- The Σ terms are **statewide weighted averages** of `PLRS·IDF·GCF` and `AV·ARF·IDF·GCF` respectively, weighted by `s_i` (plan share). They serve as denominators normalizing each plan against the state.

The formula is per-member-per-month; the dollar transfer is `T(i) × billable_member_months`.

**Sign convention:** Positive `T(i)` = the plan **receives** money. Negative = the plan **pays** in.
</transfer_formula>

<two_sides>
The formula has a clear two-side structure:

**Left side — "Revenue need based on risk":**
```
PLRS_i · IDF_i · GCF_i / Σ_state(PLRS · IDF · GCF)
```
This is the plan's normalized claim on aggregate risk. A plan with a sicker-than-average population (high PLRS) and a higher-cost metal level (high IDF) gets a larger left-side fraction.

**Right side — "Premium revenue already collected":**
```
AV_i · ARF_i · IDF_i · GCF_i / Σ_state(AV · ARF · IDF · GCF)
```
This is the plan's normalized share of premium revenue based on plan attributes (AV, age mix, induced demand, geography). It approximates what the plan *already* gets in premium absent risk adjustment.

The transfer rebalances: **(what risk says you need) − (what premium structure already gave you) × statewide average premium**.

A plan with PLRS proportional to its (AV, ARF) profile gets `T(i) ≈ 0` — the premium structure already covers it. A plan with PLRS far above its AV/ARF profile gets a positive transfer.
</two_sides>

<component_details>
**PLRS (Plan Liability Risk Score):**
- Computed by the HHS-HCC model
- Equals the enrollee-month-weighted average of `CSR_ADJUSTED_SCORE_<metal>` across all the plan's enrollees
- Note: PLRS uses the **CSR-adjusted score**, not the raw score
- A plan's PLRS varies by metal because (a) the coefficient column used differs by metal, and (b) the CSR adjustment factor differs by HIOS variant
- Higher AV plans tend to produce higher PLRS for the same enrollee, because the per-metal coefficients are calibrated to the higher liability of richer plans (Platinum coefficients > Bronze coefficients for the same HCC)

**IDF (Induced Demand Factor):**
- Captures the additional utilization induced by lower cost-sharing
- Schedule (PY2025, illustrative — verify against the published NBPP for the user's benefit year):

| Metal | IDF |
|---|---|
| Catastrophic | 1.00 |
| Bronze | 1.00 |
| Silver | 1.03 |
| Gold | 1.08 |
| Platinum | 1.15 |

- For CSR variants, the Silver IDF is replaced by metal-specific values (e.g., Silver 73 AV gets an IDF reflecting reduced cost share)
- Multiplied with PLRS on the left side and AV·ARF on the right side

**GCF (Geographic Calibration Factor):**
- One value per rating area within a state
- Captures provider price differences across geographies
- Published annually by CMS

**AV (Actuarial Value):**
- Catastrophic ≈ 0.57
- Bronze ≈ 0.60 (range 0.58-0.62)
- Silver ≈ 0.70 (CSR Silver 73 = 0.73, Silver 87 = 0.87, Silver 94 = 0.94)
- Gold ≈ 0.80
- Platinum ≈ 0.90
- Used as a proxy for plan generosity in the right side of the equation

**ARF (Allowable Rating Factor):**
- Federal age curve: ranges from ~0.635 (age 0-14) to 3.000 (age 64+)
- 3:1 max age rating ratio mandated by ACA (some states use compressed curves like NY's 1:1)
- Plan-level ARF = enrollee-month-weighted average of individual ARFs

**s_i (Plan share):**
- Plan i's share of total statewide market enrollment (same market segment)
- Used as the weight in computing the statewide weighted averages in the denominators
</component_details>

<metal_level_optimization>
The risk transfer formula creates a non-trivial relationship between metal level and net revenue. Moving an enrollee from Gold to Platinum changes both sides of the equation:

- **Left side increase:** IDF goes 1.08 → 1.15 (multiplicative on PLRS). For high-PLRS members, this is a large dollar increase.
- **Right side increase:** AV goes 0.80 → 0.90 (multiplicative with IDF). The right side also grows.

For **low-PLRS** members (e.g., a healthy 64-year-old with high ARF), the right-side increase exceeds the left-side increase → moving to Platinum *decreases* net revenue (already-large negative transfer becomes more negative, plus higher premium does not fully compensate).

For **high-PLRS** members (e.g., a young hemophiliac with PLRS > 40), the left-side increase exceeds the right-side increase → moving to Platinum *increases* net revenue (transfer grows enough that combined with the ~12% premium uplift it nets out positive).

**Inflection point** (algebraic derivation in the metal-level optimization paper):
```
PLRS_i_critical = 2.44286 · ARF_i · PLRS_s / (AV_s · ARF_s)
```
where the `_s` quantities are statewide weighted averages.

If `PLRS_i > PLRS_i_critical`: enrolling the member in Platinum is favorable (purely from a transfer perspective).
If `PLRS_i < PLRS_i_critical`: keep in Gold (or move down).

The constant `2.44286` derives from the IDF ratio `(1.15 - 1.08) / (0.9 · 1.15 - 0.8 · 1.08)` ≈ `0.07 / 0.171`. It assumes constant PLRS across metals, which is conservative (actual PLRS usually grows when moving to Platinum because per-metal coefficients are higher).

**Practical applications:**
1. Disease management / care coordination programs targeted at high-PLRS members can include metal-level migration as a tactic.
2. Plan design: pricing Platinum competitively for chronic-condition disease segments can attract favorable risk.
3. Marketing constraints: ACA's guaranteed-issue and community-rating rules limit how an issuer can directly steer enrollment, but plan benefit design and premium positioning are levers.
</metal_level_optimization>

<settlement_mechanics>
- Transfers are calculated annually by CMS using EDGE (External Data Gathering Environment) submissions from issuers
- Issuers submit enrollment, claims, and pharmacy data to EDGE on a rolling basis throughout the benefit year
- The "interim" transfer estimate is published in mid-year-following (e.g., June 2025 for BY2024)
- The "final" transfer settlement happens later, after all EDGE corrections
- An issuer's net transfer is the sum across all plans within a state-market combination — losses on one plan can offset gains on another
- High-risk pool reinsurance (when active) is calculated separately from risk adjustment but interacts with overall economics
</settlement_mechanics>

<relationship_to_risk_score>
**Important:** The HHS-HCC risk score is **one input** to the transfer. Decisions optimized only against risk score may be wrong from a transfer perspective.

| Goal | What to optimize |
|---|---|
| Maximize risk score | Maximize HCC capture, accurate diagnosis coding |
| Maximize transfer received | Risk score relative to AV/ARF profile, given statewide context |
| Maximize net revenue | Transfer + premium − claims − admin |

A plan can have high PLRS and still pay into the pool if the right side (AV·ARF·IDF) is even higher. Conversely, a plan with average PLRS but very low AV·ARF can still receive a transfer if the population is older or sicker than its AV bucket would suggest.

**HCC accuracy is necessary but not sufficient** — the population composition by AV/ARF and the statewide context determine the actual transfer.
</relationship_to_risk_score>

<canonical_data>
- Annual CMS publications for each parameter:
  - IDF schedule: in the annual NBPP final rule
  - GCF table: annual NBPP technical specifications
  - Federal age curve / ARF: ACA standard, codified at 45 CFR § 147.102
  - AV calculator: HHS-published Actuarial Value Calculator (annual)
  - PLRS: derived from the HHS-HCC model output for that benefit year
  - Statewide averages (P̄_s, weighted PLRS·IDF·GCF, weighted AV·ARF·IDF·GCF): published in the CMS Risk Adjustment Summary Report after the benefit year settlement
- The `RA_FACTOR` / CSR multiplier in the score formula is separate from the IDF in the transfer formula — see `references/csr-adjustments.md`
</canonical_data>
