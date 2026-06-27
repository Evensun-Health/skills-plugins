# Workflow: Calculate a Risk Score for an Enrollee

<required_reading>
**Read these references first:**
1. `references/model-overview.md` — to identify the right sub-model
2. The relevant sub-model reference based on age:
   - `AGE_LAST >= 21`: `references/adult-model.md`
   - `AGE_LAST 2-20`: `references/child-model.md`
   - `AGE_LAST 0-1`: `references/infant-model.md`
3. `references/csr-adjustments.md` if the user mentions a CSR variant
</required_reading>

<process>
## Step 1: Confirm benefit year

**Always ask the user what benefit year they want to use** before scoring. Do not assume. Coefficients change every year and several model rules (severity placements, group flags, CSR factors) change at year boundaries.

Example: "What benefit year should I use? (e.g., BY2023, BY2024, BY2025)"

## Step 2: Gather inputs

You need:
- **DOB or AGE_LAST** (and SEX: M or F)
- **METAL letter** (P/G/S/B/C) or full name
- **CSR_INDICATOR** (numeric code) — or the HIOS plan suffix to derive it
- **Benefit year** — REQUIRED. Always ask the user explicitly. Coefficients change every year and several model rules (severity placements, group flags, CSR factors) change at year boundaries. Do not assume a default.
- **Flagged HCCs** (e.g., `["HHS_HCC042", "HHS_HCC156"]`) — already after hierarchy and grouping, or pre-hierarchy if you'll need to apply hierarchy yourself
- **Flagged RXCs** (Adult only, e.g., `["RXC_09"]`)
- **ENROLDURATION** (months enrolled, integer 1-12; only matters for Adult HCC_ED)

If the user gives you raw diagnoses instead of HCCs, that requires the DX→CC→HCC pipeline — which the script does not implement. In that case, redirect: tell the user this workflow scores from already-flagged HCCs, and to compute from raw diagnoses they need either the user's SQL implementation (for batch use) or the CMS Python tooling.

**Important upstream filter — qualifying claims:** Diagnoses only contribute to risk score if they appear on a qualifying medical claim (inpatient bill type 111-114/117 auto-qualifies; outpatient UB and professional CMS-1500 require a CPT/HCPCS on the CMS qualifying-services list). Lab claims, DME, and J-code-only claims do not qualify even when they carry HCC-mapped DX codes. If the user is asking why a known diagnosis isn't producing an HCC, point them to `references/claim-qualification.md` before running the scorer — the answer is often "the claim isn't qualifying."

## Step 3: Run the scorer

Use `scripts/score_enrollee.py`:

```bash
python3 /Users/wesley/.claude/skills/hhs-hcc-risk-adjustment/scripts/score_enrollee.py \
  --age 45 --sex F --metal S --csr 1 --year 2025 \
  --hcc HHS_HCC042 HHS_HCC156 \
  --rxc RXC_09 \
  --enrol-duration 12
```

The script:
1. Picks Adult/Child/Infant based on `--age`
2. Validates HCCs against the model's variable list
3. Auto-derives severe/transplant/HCC_ED counters from inputs
4. Auto-derives RXC × HCC interactions
5. Multiplies the indicator vector by the coefficient column for the metal
6. Applies the CSR multiplier
7. Prints both raw and CSR-adjusted scores plus a per-variable contribution breakdown

## Step 4: Interpret the output

The script outputs:
- **Sub-model used** (Adult / Child / Infant)
- **Per-variable contributions** (variable, indicator value, coefficient, contribution)
- **Raw score** = sum of contributions
- **CSR-adjusted score** = raw × `RA_Factor(CSR_INDICATOR)`

If the user wanted the **plan-level** PLRS, this is just one enrollee — they'd need to weight by member months across all enrollees in the plan. Mention that if the question implies plan-level work.

## Step 5: Sanity-check

If the score looks unexpected:
- Verify the sub-model boundary (`AGE_LAST` exactly: 21+, 2-20, 0-1)
- For infants: verify the maturity bucket (infant scoring is dominated by maturity × severity, not raw HCCs — see `references/infant-model.md`)
- For adults with high HCC count: verify severity buckets fired (the SEVERE_HCC_COUNT* coefficients are large, often negative for low counts and positive for high counts)
- For BY2025 child enrollees with high HCC count: confirm bucket aliasing (SEVERE_6/7 share value, SEVERE_8/9/10 share value, TRANSPLANT_4-8 share value) — see `references/coefficient-data.md`. The same aliasing applies to other years where the child model uses collapsed buckets.
</process>

<success_criteria>
This workflow is complete when:
- [ ] All inputs are gathered (or missing inputs flagged with reasonable defaults)
- [ ] The scorer ran without error
- [ ] The user has the raw and CSR-adjusted score
- [ ] The user has a per-variable breakdown they can audit
- [ ] Sub-model selection and any unusual coefficient sources were disclosed
</success_criteria>
