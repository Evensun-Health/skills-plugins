<overview>
The HHS-HCC model is a concurrent (same-year) risk adjustment model used to redistribute premium revenue across issuers in the ACA individual and small-group markets. Unlike the Medicare CMS-HCC model, which is prospective (uses prior-year diagnoses to predict next-year costs), HHS-HCC uses **same-year** diagnoses to score the **same-year** plan liability.

The model is published annually by CMS via the Notice of Benefit and Payment Parameters (NBPP) — typically a draft NBPP in late Q4 of the year prior to the benefit year, and a final NBPP in early Q1 of the benefit year.
</overview>

<model_versions>
| Model family | Benefit years | Notes |
|---|---|---|
| V01-V04 | 2014-2017 | Pre-V05 versions, ICD-9 era and early ICD-10 |
| **V05** | **2018-2020** | First "modern" version, 128 HCCs |
| **V07** | **2021 onward** | 141 HCCs |

Within V07, every benefit year gets a release tag (e.g., `V0721.141.A3` = released 07/2021, model 141, A-series version 3). The letter sequence maps roughly to benefit year (A=2021, B=2022, C=2023, D=2024, E=2025).

This skill focuses on V07. V05 details exist in the SAS source archive under `/Users/wesley/Documents/CMS HHS-HCC Model/SAS/` if needed.
</model_versions>

<sub_models>
Every enrollee is scored under exactly one sub-model based on `AGE_LAST` (age on the last day of the benefit year, OR last day of enrollment if disenrolled mid-year):

<sub_model name="Adult">
- **Range:** `AGE_LAST >= 21`
- **Variables:** age/sex (9 male + 9 female bins from 21_24 to 60_GT), HCCs, group flags (G01, G02B, G04, G06A, G08, G09A, G09C, G10, G11, G12, G13, G14, G21, G15A, G16, G17A, G18A, G24), severe counters (1-9, 10PLUS), transplant counters (4-7, 8PLUS), HCC_ED1-6 (HCC-contingent enrollment duration), 10 RXC variables, RXC × HCC interaction flags
- **Score formula:** `score = sum(indicator × coefficient)` over all flagged variables, picking the column matching the enrollee's METAL letter (P/G/S/B/C)
- See `references/adult-model.md`
</sub_model>

<sub_model name="Child">
- **Range:** `AGE_LAST in [2, 20]` (note: not `[2, 18]` — children includes through age 20)
- **Variables:** age/sex (4 male + 4 female bins from 2_4 to 15_20), HCCs, group flags (overlapping but distinct from adult — includes G02D, G03, G19B, G22, G23 not in adult; excludes G15A, G21, G24), severe counters (1-5, **6_7**, **8PLUS** — note collapsed buckets), transplant counter (**4PLUS** only)
- **No RXC variables** — the child model does not use prescription drug categories
- See `references/child-model.md`
</sub_model>

<sub_model name="Infant">
- **Range:** `AGE_LAST in [0, 1]`
- **Variables:** AGE0_MALE, AGE1_MALE (no female age-sex add-ons), maturity flags (IHCC_EXTREMELY_IMMATURE, IHCC_IMMATURE, IHCC_PREMATURE_MULTIPLES, IHCC_TERM, IHCC_AGE1), severity flags (IHCC_SEVERITY1-5), and 25 maturity × severity interaction flags (the actual scoring variables)
- **Structurally different** — no HCC group collapsing, no severe/transplant counters, no RXCs. The maturity × severity interaction is the entire payment mechanism.
- See `references/infant-model.md`
</sub_model>
</sub_models>

<scoring_pipeline>
The end-to-end pipeline for one enrollee:

```
1. Demographics in (DOB, sex, METAL, CSR_INDICATOR, ENROLDURATION)
   ↓
2. Diagnoses in (ICD-10 codes with service dates)
   ↓
3. DX → CC mapping (apply effective dates, age/sex/MCE edits)
   ↓
4. CC → HCC hierarchy (e.g., HCC008=1 zeros HCC009-013)
   ↓
5. Group collapsing (Adult/Child only — G01 zeros HCC019-021, etc.)
   ↓
6. Pharmacy/HCPCS → RXC mapping (Adult only, AGE_LAST > 20)
   ↓
7. RXC hierarchy (RXC_06=1 zeros RXC_07)
   ↓
8. Set severity / transplant counters (Adult/Child)
   Set maturity × severity interactions (Infant)
   Set HCC_ED1-6 (Adult only, gated on HCC count > 0)
   Set RXC × HCC interactions (Adult only)
   ↓
9. Score = Σ (indicator × coefficient_for_metal_level)
   ↓
10. CSR-adjusted score = score × RA_Factor (looked up from CSR_INDICATOR)
```

The `score` is the variable-level sum. The `CSR_ADJUSTED_SCORE` applies the variant's CSR multiplier (e.g., Silver 87% AV gets 1.12 in PY2025).
</scoring_pipeline>

<key_terminology>
| Term | Meaning |
|---|---|
| **CC** | Condition Category — intermediate category before hierarchy is applied |
| **HCC** | Hierarchical Condition Category — CC after hierarchy |
| **Group flag (G##)** | Combined HCC indicator that replaces individual HCCs in payment scoring (e.g., G14 replaces HCC128/HCC129) |
| **RXC** | Prescription Drug Category — payment variable derived from NDC and HCPCS J-codes |
| **MCE edit** | Medicare Code Editor age/sex edits — a code is invalid for an out-of-range demographic |
| **AGE_LAST** | Age on the last day of the enrollee's enrollment span in the benefit year |
| **METAL** | Plan metal level: Platinum (P), Gold (G), Silver (S), Bronze (B), Catastrophic (C) |
| **CSR_INDICATOR** | Numeric code for the cost-sharing reduction variant of the plan, derived from HIOS plan ID suffix |
| **ENROLDURATION** | Number of months enrolled in the benefit year (1-12) |
| **NBPP** | Notice of Benefit and Payment Parameters — annual CMS regulation publishing the model |
</key_terminology>

<scope_boundary>
The HHS-HCC model **does not** apply to:
- Medicare Advantage / CMS-HCC (use the V28 / V24 Medicare model instead)
- Medicaid managed care (state-specific models)
- Stand-alone dental or vision plans
- Large-group commercial (no risk adjustment program)
</scope_boundary>
