---
name: hhs-hcc-transfer
description: Compute a CMS risk transfer payment T(i) per billable member-month, or find the PLRS inflection point where a Platinum metal strategy beats Gold. Optionally looks up statewide inputs from the bundled statewide_ra_factors.csv.
---

Ask the user which mode they want:

1. **Transfer** — compute T(i) for a plan given its plan-level and statewide inputs
2. **Inflection** — find the PLRS at which Platinum becomes favorable over Gold (transfer-only perspective)

---

### Transfer mode

Collect:

**Plan-level inputs:**
- `PLRS` — Plan Liability Risk Score
- `IDF` — Induced Demand Factor
- `GCF` — Geographic Calibration Factor
- `AV` — Actuarial Value (e.g. 0.80 for Gold)
- `ARF` — Allowable Rating Factor

**Statewide inputs:**
- Statewide weighted-average PLRS, IDF, GCF, AV, ARF
- Statewide average premium P̄

**Offer to look up statewide values:** If the user provides a state abbreviation and benefit year, grep `${CLAUDE_PLUGIN_ROOT}/skills/hhs-hcc-risk-adjustment/data/statewide_ra_factors.csv` for matching rows and present the available market options (Market 1 = Individual, Market 2 = Small Group). Let the user select the right market and confirm the values before running.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py" \
  --plrs PLRS --idf IDF --gcf GCF --av AV --arf ARF \
  --statewide-plrs SW_PLRS --statewide-idf SW_IDF --statewide-gcf SW_GCF \
  --statewide-av SW_AV --statewide-arf SW_ARF \
  --premium PBAR
```

After running, explain:
- Whether the plan receives or pays a transfer and why (PLRS vs. statewide average, metal AV)
- The magnitude in annualized terms (multiply per-member-month result × 12 × estimated enrollment)
- What levers would shift the transfer (PLRS improvement, metal-level mix, GCF)

---

### Inflection mode

Collect:
- Plan ARF
- Statewide PLRS, AV, ARF

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py" \
  --inflection --arf ARF \
  --statewide-plrs SW_PLRS --statewide-av SW_AV --statewide-arf SW_ARF
```

Explain the result: if projected PLRS exceeds the inflection point, Platinum is favorable from a transfer-only perspective. Note this is before considering the premium revenue difference between metals.
