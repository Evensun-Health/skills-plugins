<scope>
Infant model rules: applies to enrollees with `AGE_LAST in [0, 1]`. The infant model is structurally distinct from Adult/Child — there are no HCC group flags, no severe/transplant counters, and no RXC variables. Payment is driven by a maturity × severity interaction grid plus optional age-sex add-ons. Verified against CMS SAS source for BY2018-BY2024 and the BY2025 DIY tables / Python release.
</scope>

<demographic_addon>
Only two age-sex add-ons (no female counterparts):
- `AGE0_MALE` — set when `AGE_LAST = 0 AND SEX = 'M'`
- `AGE1_MALE` — set when `AGE_LAST = 1 AND SEX = 'M'`

Females and the maturity bucket carry the female-baseline implicitly through the maturity × severity coefficients.
</demographic_addon>

<maturity_categories>
5 maturity flags, exactly one set per infant after hierarchy:

| Flag | Trigger | Notes |
|---|---|---|
| `IHCC_EXTREMELY_IMMATURE` | `AGE_LAST=0 AND (HCC242 OR HCC243 OR HCC244)` | Highest priority |
| `IHCC_IMMATURE` | `AGE_LAST=0 AND (HCC245 OR HCC246)` | |
| `IHCC_PREMATURE_MULTIPLES` | `AGE_LAST=0 AND (HCC247 OR HCC248)` | |
| `IHCC_TERM` | `AGE_LAST=0 AND HCC249` | |
| `IHCC_AGE1` | `AGE_LAST=1` OR `AGE_LAST=0 with no maturity HCCs` | Catchall |

**Maturity hierarchy (high to low):** EXTREMELY_IMMATURE > IMMATURE > PREMATURE_MULTIPLES > TERM > AGE1. After all candidate flags are set, the highest one wins and the others are zeroed.

**Critical rule:** the maturity flags are gated to `AGE_LAST = 0` enrollees. An `AGE_LAST = 1` enrollee always gets `IHCC_AGE1 = 1` regardless of any HCC242-249 flags they may have.
</maturity_categories>

<severity_categories>
5 severity flags, highest wins:

| Flag | Triggering HCCs (PY2025) |
|---|---|
| `IHCC_SEVERITY5` | HCC008, 018, 034, 041, 042, 125, 128, 129, 130, 137, 158, 183, 184, 251 |
| `IHCC_SEVERITY4` | HCC002, 009, 026, 030, 035_1, 035_2, **064**, 067, 068, 073, 106, 107, 111, 112, 115, 122, 126, 127, 131, 135, 138, 145, 146, 154, 156, 163, 187, 253 |
| `IHCC_SEVERITY3` | HCC001, 003, 006, 010, 011, 012, 027, 045, 054, 055, 061, 063, 066, **070** *(BY2025+)*, 074, 075, 081, 082, 083, 084, 096, 108, 109, 110, 113, 114, 117, 119, 121, 132, 139, 142, 149, 150, 159, 218, 223, 226, 228 |
| `IHCC_SEVERITY2` | HCC004, 013, 019, 020, 021, 023, **028**, 029, 036, 046, 047, 048, 056, 057, 062, 069, **070** *(≤BY2024)*, **071** *(BY2025+)*, 097, 120, 151, 153, 160, 161_1, 162, 188, 217, 219 |
| `IHCC_SEVERITY1` | HCC037_1, 037_2, **071** *(≤BY2024)*, 102, 103, 118, 161_2, 234, 254 |

Default: if no severity HCC fires, set `IHCC_SEVERITY1 = 1`.

**Year notes:**
- HCC064→SEVERITY4, HCC028→SEVERITY2: canonical every year (BY2018+).
- **HCC070, HCC071: reassigned in BY2025** as part of the sickle cell disease cost prediction update (NBPP 2025). HCC070 moved SEVERITY2 → SEVERITY3; HCC071 moved SEVERITY1 → SEVERITY2. The old assignments apply to BY2024 and earlier.

**Hierarchy:** SEVERITY5 > SEVERITY4 > SEVERITY3 > SEVERITY2 > SEVERITY1. Highest wins; others zeroed.
</severity_categories>

<maturity_x_severity_grid>
The actual scoring variables are 25 maturity × severity interaction flags:

```
EXTREMELY_IMMATURE_X_SEVERITY5  ...  EXTREMELY_IMMATURE_X_SEVERITY1
IMMATURE_X_SEVERITY5            ...  IMMATURE_X_SEVERITY1
PREMATURE_MULTIPLES_X_SEVERITY5 ...  PREMATURE_MULTIPLES_X_SEVERITY1
TERM_X_SEVERITY5                ...  TERM_X_SEVERITY1
AGE1_X_SEVERITY5                ...  AGE1_X_SEVERITY1
```

Set as the AND of the corresponding maturity flag and severity flag. Because both axes are mutually exclusive after their hierarchies, exactly **one** of these 25 fires per infant.

PY2025 coefficients (Platinum) range from `0.581` (AGE1_X_SEVERITY1) to `204.04` (EXTREMELY_IMMATURE_X_SEVERITY5). The variation is huge — getting an infant's bucket wrong by even one tier can change the score by a factor of 2-5.
</maturity_x_severity_grid>

<age0_male_swap>
**Critical rule** (canonical per CMS SAS source for BY2018-BY2024 and DIY tables for BY2024-BY2025; **omitted from CMS Python BY2025 — Python is wrong here**):

```
if AGE_LAST = 0 and IHCC_AGE1 = 1 and AGE0_MALE = 1 then do;
   AGE1_MALE = 1;
   AGE0_MALE = 0;
end;
```

This reassigns the demographic add-on for 0-year-old males whose maturity bucket fell through to `IHCC_AGE1` (i.e., they have no HCC242-249 birth code). It moves them from the larger `AGE0_MALE` coefficient (~0.604 Platinum) to the smaller `AGE1_MALE` (~0.09 Platinum). Without this swap, scores are inflated by ~0.5 for these specific infants.

The CMS Python release at `software/HHS_HCC/utils.py` for BY2025 does not implement this swap. Treat the SAS source / DIY tables as canonical.
</age0_male_swap>

<no_hcc_grouping>
The infant model **does not** apply HCC group collapsing. HCCs that get collapsed in Adult/Child (e.g., HCC019/020/021 → G01) remain as standalone HCCs in the infant model. This matters when reading severity HCC lists — they reference the standalone HCC numbers, not Group flags.

Note that the Adult/Child group collapsing logic is gated on age, so it correctly skips infants when implemented properly.
</no_hcc_grouping>

<scoring_formula>
```
SCORE_INFANT_<metal> = Σ (variable_indicator × variable_coefficient_<metal>)
```
where variables are: AGE0_MALE, AGE1_MALE, and the 25 maturity × severity flags. Note that **infant HCCs themselves do not contribute coefficients directly** — they only contribute through the severity classification.

Final score and CSR adjustment follow the same shape as Adult/Child.
</scoring_formula>

<canonical_data>
PY2025 coefficients: `/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/infant_model_factors.csv`

Maturity mapping: `infant_maturity_mappings.csv`.
Severity mapping: `infant_severity_mappings.csv` (note: this is the BY2025 mapping; for prior years use the CMS SAS source under `/Users/wesley/Documents/CMS HHS-HCC Model/SAS/`).
</canonical_data>
