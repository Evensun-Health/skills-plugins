# Workflow: Compute or Analyze a CMS Risk Transfer

<required_reading>
1. `references/risk-transfer-formula.md` — full formula, components, metal-level inflection point derivation
2. `references/csr-adjustments.md` — only if the user is also asking about CSR factors (different from IDF — easy to confuse)
</required_reading>

<process>
## Step 1: Identify what the user actually wants

Common framings:
- **"What's our transfer for plan X?"** — they want T(i) given known plan-level inputs
- **"Should this member be on Platinum or Gold?"** — metal-level inflection point analysis
- **"Why did our transfer go down?"** — diagnostic; need PLRS, AV/ARF mix, statewide context
- **"What's PLRS?"** — definitional; route to `references/risk-transfer-formula.md` instead

## Step 2: Confirm benefit year

**Always ask the user explicitly.** IDF schedules, GCF tables, federal age curve, statewide weighted averages all change year over year. Do not assume.

## Step 3: Gather inputs

For computing a transfer T(i):
- **Plan-specific:**
  - PLRS_i (the plan's risk score; from prior workflow output or reported by the user)
  - IDF_i (metal-level induced demand factor)
  - GCF_i (rating-area geographic calibration factor; from CMS published tables)
  - AV_i (plan actuarial value)
  - ARF_i (plan-level Allowable Rating Factor — enrollee-month-weighted average)
- **Statewide:**
  - Weighted-average PLRS·IDF·GCF
  - Weighted-average AV·ARF·IDF·GCF
  - P̄_s (statewide average premium)

For metal-level inflection point analysis:
- Member's projected PLRS_i
- Member's ARF_i
- Statewide PLRS_s, AV_s, ARF_s

## Step 4: Run the calculator

```bash
python3 /Users/wesley/.claude/skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py \
  --plrs 1.8 --idf 1.08 --gcf 1.09 \
  --av 0.8 --arf 1.90 \
  --statewide-plrs 1.5 --statewide-idf 1.03 --statewide-gcf 1.0 \
  --statewide-av 0.686 --statewide-arf 1.541 \
  --premium 375
```

Output: T(i) per member-month, with the left-side and right-side fractions broken out.

For the inflection point:
```bash
python3 /Users/wesley/.claude/skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py \
  --inflection \
  --arf 1.541 --statewide-plrs 1.5 --statewide-av 0.686 --statewide-arf 1.541
```

Output: the critical PLRS above which Platinum is favorable for that ARF.

## Step 5: Interpret

The transfer formula has two fractions; their difference times statewide premium is the per-member-month transfer:
- Left side dominant (large positive PLRS·IDF·GCF relative to AV·ARF·IDF·GCF) → **receive** money
- Right side dominant → **pay** money
- Roughly equal → near-zero transfer

A negative transfer is not necessarily bad. A young low-risk plan paying into the pool is doing what risk adjustment is designed to do. Net plan economics is `transfer + premium − claims − admin`.

## Step 6: Disclose assumptions

Always state:
- Which benefit year's IDF schedule and statewide averages are used
- Whether statewide values came from the user, from a published CMS Risk Adjustment Summary Report, or are estimates
- If the user is asking pre-settlement, note that final statewide weights aren't known until CMS publishes them after the benefit year ends
</process>

<success_criteria>
This workflow is complete when:
- [ ] Year confirmed
- [ ] All required inputs gathered or estimated with disclosure
- [ ] T(i) (or inflection PLRS) computed
- [ ] Left-side / right-side decomposition shown so the user can see what drove the result
- [ ] Limitations and statewide-input assumptions disclosed
</success_criteria>
