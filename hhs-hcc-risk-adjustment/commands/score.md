---
name: hhs-hcc-score
description: Score an ACA enrollee under the HHS-HCC risk adjustment model. Collects demographics, flagged HCCs/RXCs, and benefit year, then runs score_enrollee.py and explains the result.
---

Collect the following inputs conversationally. If the user already provided some in their message, skip those questions.

**Required:**
- **Benefit year** — BY2018–BY2027. Always confirm this first; coefficients change annually.
- **Age** — `AGE_LAST` (age on the last day of the benefit year)
- **Sex** — M or F
- **Metal level** — Platinum, Gold, Silver, Bronze, or Catastrophic
- **CSR indicator** — the `RA_CSR_Indicator` for this enrollment span:
  - `1` = Standard plan, no CSR (most Bronze/Gold/Platinum, and Silver plans not receiving CSR)
  - `3` = Silver state-subsidy (HIOS variants 05/06/07, 30–36)
  - `4` = Zero Cost Share Platinum | `5` = LCS Platinum | `6` = ZCS Silver | `7` = LCS Silver
  - `8` = ZCS Gold | `9` = LCS Gold | `10` = ZCS Bronze | `11` = LCS Bronze | `12` = ZCS Platinum
  - If unsure, ask for the last two digits of the 16-character HIOS plan ID.
- **Flagged HCCs** — space-separated list of HCC variable names **after hierarchy and group collapsing** (e.g. `HHS_HCC042 HHS_HCC156`). Remind the user: inputs must be post-hierarchy; do not pass both an HCC and an HCC it supersedes.

**Optional:**
- **Flagged RXCs** — Adult model only (e.g. `RXC_09`). Skip for Child/Infant.
- **Enrollment duration** — months enrolled (1–12). Only relevant if < 7 months and the enrollee has at least one HCC; triggers the `HCC_ED` short-enrollment flag.

Once you have the inputs, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/hhs-hcc-risk-adjustment/scripts/score_enrollee.py" \
  --age AGE --sex SEX --metal METAL --csr CSR --year YEAR \
  --hcc HCC1 HCC2 ... \
  --rxc RXC1 ... \
  --enrol-duration MONTHS
```

Omit `--rxc` if no RXCs. Omit `--enrol-duration` if not provided.

After running, present the output table and then:
1. Identify the top contributing variables and explain what each HCC/RXC/interaction represents clinically.
2. Note any severity or transplant counter that fired and why.
3. Show the CSR-adjusted final score and explain the CSR factor applied.
4. Flag anything surprising (e.g. an expected HCC that didn't appear — check if it was superseded by a hierarchy).
