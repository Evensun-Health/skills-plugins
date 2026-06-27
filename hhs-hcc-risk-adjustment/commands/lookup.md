---
name: hhs-hcc-lookup
description: Look up a coefficient from the HHS-HCC model by variable name, benefit year, and metal level. Handles HCCs, group flags, RXCs, interaction terms, age/sex variables, severity/transplant counters, and infant maturity×severity variables.
---

Collect the following. If the user already provided them in their message, proceed directly.

- **Variable name** — the exact model variable (e.g. `HHS_HCC042`, `G01`, `RXC_09`, `EXTREMELY_IMMATURE_X_SEVERITY5`, `SEVERE_HCC_COUNT3`, `MAGE_LAST_45_49`). If the user gives a description instead of a variable name (e.g. "heart failure"), look it up in `data/hcc_labels.csv` using Grep first.
- **Benefit year** — BY2018–BY2027.
- **Model** — Adult, Child, or Infant. If not provided, infer from the variable type (infant maturity/severity variables → Infant; G-prefix group flags → Adult or Child as applicable).
- **Metal level** — Platinum, Gold, Silver, Bronze, Catastrophic. If omitted, return all five.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/hhs-hcc-risk-adjustment/scripts/lookup.py" \
  --year YEAR --model MODEL --variable VARIABLE [--metal METAL]
```

Present the result and add brief context:
- What condition or model construct the variable represents
- Whether the variable is in the severity/transplant bucket set
- Any year-over-year note if the user might be comparing to a prior year value (check `references/year-changes.md` for changes affecting this variable)
