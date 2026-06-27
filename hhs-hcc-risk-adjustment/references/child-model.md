<scope>
Child model rules: applies to enrollees with `AGE_LAST in [2, 20]`. Verified against CMS SAS source for BY2018-BY2024 and the CMS Python release for BY2025.
</scope>

<age_sex_variables>
4 male and 4 female bins:
```
MAGE_LAST_2_4, MAGE_LAST_5_9, MAGE_LAST_10_14, MAGE_LAST_15_20
FAGE_LAST_2_4, FAGE_LAST_5_9, FAGE_LAST_10_14, FAGE_LAST_15_20
```
Exactly one set per enrollee.
</age_sex_variables>

<group_flags>
PY2025 child group flags (note: distinct from adult — different Group set):

| Group | Members |
|---|---|
| G01 | HCC019, HCC020, HCC021 |
| G02B | HCC026, HCC027 |
| G02D | HCC028, HCC029 |
| G03 | HCC054, HCC055 |
| G04 | HCC061, HCC062 |
| G06A | HCC067, HCC068, HCC069 |
| G08 | HCC073, HCC074 |
| G09A | HCC081, HCC082 |
| G09C | HCC083, HCC084 |
| G10 | HCC106, HCC107 |
| G11 | HCC108, HCC109 |
| G12 | HCC117, HCC119 |
| G13 | HCC126, HCC127 |
| G14 | HCC128, HCC129 |
| G23 | HCC131, HCC132 |
| G16 | HCC187, HCC188 |
| G17A | HCC204, HCC205 |
| G18A | HCC207, HCC208 |
| G19B | HCC210, HCC211 |
| G22 | HCC234, HCC254 |

**Adult-only groups not in Child:** G15A, G21, G24
**Child-only groups not in Adult:** G02D, G03, G19B, G22, G23
**Common to both:** G01, G02B, G04, G06A, G08, G09A, G09C, G10, G11, G12, G13, G14, G16, G17A, G18A

**Year notes:**
- `G07A` (HCC070, HCC071) existed BY2018-BY2024 in both Adult and Child models, removed in BY2025.
- The child group set has been more stable than the adult set.
</group_flags>

<hcc_count>
Same rules as Adult: exclude HHS_HCC022; group flags count, individual HCCs that got collapsed do not.
</hcc_count>

<severe_counters>
**Different bucket structure than Adult.** 7 buckets:
```
SEVERE_HCC_COUNT1, COUNT2, COUNT3, COUNT4, COUNT5, COUNT6_7, COUNT8PLUS
```

The `COUNT6_7` bucket fires when `HCC_CNT in {6, 7}`. The `COUNT8PLUS` fires when `HCC_CNT >= 8`. This collapsing reflects smaller sample sizes in pediatric populations.

**Child severe list (PY2025):**
HHS_HCC002, 003, 004, 006, **018**, 023, 034, 041, 042, 096, 121, 122, 125, 135, 145, 156, 158, 163, **183**, 218, 223, 251, **G13, G14**

Differences from adult severe list:
- Adds HCC018, HCC183 (in adult, these collapse into G24 which IS in adult's severe list)
- Removes G24 (G24 doesn't exist in child model)
</severe_counters>

<transplant_counters>
**Single bucket** (vs 5 in adult):
```
TRANSPLANT_HCC_COUNT4PLUS
```
Fires when at least one transplant HCC AND `HCC_CNT >= 4`.

**Child transplant list (PY2025):**
HHS_HCC**018**, 034, 041, 158, **183**, 251, G14

Differences from adult: adds HCC018, HCC183 (same reason as severe); excludes G24.
</transplant_counters>

<no_rxc>
The child model **does not** use RXC variables. There is no RXC × HCC interaction in the child model.
</no_rxc>

<no_hcc_ed>
The child model **does not** use HCC_ED variables. Enrollment duration is not corrected for in the child model.
</no_hcc_ed>

<scoring_formula>
Same shape as adult:
```
SCORE_CHILD_<metal> = Σ (variable_indicator × variable_coefficient_<metal>)
SCORE_CHILD = SCORE_CHILD_<metal_letter>
CSR_ADJUSTED_SCORE_CHILD = SCORE_CHILD × RA_Factor(CSR_INDICATOR)
```
</scoring_formula>

<canonical_data>
PY2025 coefficients: `/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/child_model_factors.csv`

Group mappings: `child_group_mappings.csv`.
Severe list: `severe_list.csv` (column `child` = 'y').
Transplant list: `transplant_list.csv` (column `child` = 'y').
</canonical_data>
