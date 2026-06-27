<scope>
Adult model rules: applies to enrollees with `AGE_LAST >= 21`. Variables and logic verified against CMS SAS source for BY2018-BY2024 and the CMS Python release for BY2025.
</scope>

<age_sex_variables>
9 male and 9 female bins. Exactly one is set to 1 per enrollee. The bins:

```
MAGE_LAST_21_24, MAGE_LAST_25_29, MAGE_LAST_30_34,
MAGE_LAST_35_39, MAGE_LAST_40_44, MAGE_LAST_45_49,
MAGE_LAST_50_54, MAGE_LAST_55_59, MAGE_LAST_60_GT
```

The `_60_GT` bin is open-ended (60 and older). Female bins use the `F` prefix.
</age_sex_variables>

<group_flags>
After CC hierarchies are applied, certain HCCs collapse into Group flags. The Group flag replaces the individual HCCs in payment scoring (the individuals are zeroed). PY2025 adult groups:

| Group | Members |
|---|---|
| G01 | HCC019, HCC020, HCC021 |
| G02B | HCC026, HCC027 |
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
| G21 | HCC137, HCC138, HCC139 |
| G15A | HCC160, HCC161_1, HCC161_2 |
| G16 | HCC187, HCC188 |
| G17A | HCC204, HCC205 |
| G18A | HCC207, HCC208 |
| G24 | HCC018, HCC183 |

**Year notes:**
- `G07A` (HCC070, HCC071) existed BY2018-BY2024 and was **removed in BY2025** as part of the sickle cell disease re-mapping; in BY2025 HCC070 and HCC071 are scored individually with their own coefficients.
- `G24` was added in BY2024.

The collapsing happens **after** CC hierarchies but **before** severity/transplant counter calculation. The severity/transplant counters use both Group flags AND ungrouped HCCs.
</group_flags>

<hcc_count>
`HCC_CNT` is the number of distinct flagged HCCs per enrollee, used to drive severity/transplant/HCC_ED counters. Two key rules:
1. **Exclude `HHS_HCC022`** from the count (it's a payment HCC but doesn't count toward severity).
2. **Group flags count, individual HCCs that got collapsed do not** (already zeroed by group collapsing).

Equivalent formula: `HCC_CNT = sum(all HHS_HCCxxx where xxx != 022) + sum(all G## flags)`.
</hcc_count>

<severe_counters>
The Adult model has 10 severe-count buckets, exactly one set per enrollee with severe HCCs:

```
SEVERE_HCC_COUNT1, ..., SEVERE_HCC_COUNT9, SEVERE_HCC_COUNT10PLUS
```

Set when:
- Enrollee has at least one HCC in the **adult severe list** (post- OR pre-grouping check), AND
- `HCC_CNT == n` for buckets 1-9, or `HCC_CNT >= 10` for the 10PLUS bucket

**Adult severe list (PY2025):**
HHS_HCC002, 003, 004, 006, 023, 034, 041, 042, 096, 121, 122, 125, 135, 145, 156, 158, 163, 218, 223, 251, **G13, G14, G24**

The "pre-grouping check" matters because some severe HCCs (HCC018, HCC183) collapse into G24 — both the pre-grouped HCC and the post-grouped flag should trigger the severe indicator.

Coefficients are typically negative for low counts and positive for high counts (since the marginal value of additional HCCs decreases). At HCC_CNT=10+ the coefficient is large and positive.
</severe_counters>

<transplant_counters>
5 buckets: `TRANSPLANT_HCC_COUNT4, 5, 6, 7, 8PLUS`. Set when:
- Enrollee has at least one HCC in the **adult transplant list**, AND
- `HCC_CNT == n` for 4-7, or `HCC_CNT >= 8` for 8PLUS

**Adult transplant list (PY2025):**
HHS_HCC034, 041, 158, 251, **G14, G24**

Like severe, both pre- and post-grouping flags should be checked.

Coefficients are large and positive (transplants are expensive).
</transplant_counters>

<hcc_ed_variables>
HCC-contingent enrollment duration variables for partial-year enrollees with at least one HCC. Six binary flags, exactly one set:

```
HCC_ED1 (1 month enrolled)
HCC_ED2 (2 months)
HCC_ED3 (3 months)
HCC_ED4 (4 months)
HCC_ED5 (5 months)
HCC_ED6 (6 months)
```

Set when `HCC_CNT > 0 AND ENROLDURATION == m`. Enrollees with 7+ months get nothing here (their full age-sex / HCC coefficients already represent appropriate annualized risk). The HCC_ED flags add a corrective load for short enrollments where the partial-year HCC observation under-represents annual risk.

These were introduced in BY2023. Prior years used different short-duration mechanisms.
</hcc_ed_variables>

<rxc_variables>
10 prescription drug category variables: `RXC_01` through `RXC_10`. Sourced from:
- NDC codes on pharmacy claims → `dbo.NDC_RXC` mapping
- HCPCS J-codes on medical claims → `dbo.HCPCSRXC` mapping

**RXC hierarchy:** `RXC_06 = 1` zeros `RXC_07` (immunosuppressants/transplant-related ordering).
</rxc_variables>

<rxc_hcc_interactions>
RXC × HCC interaction variables. Set when both the RXC and at least one of the listed HCCs are flagged:

| Interaction | RXC | HCC list |
|---|---|---|
| RXC_01_X_HCC001 | RXC_01 | HCC001 |
| RXC_02_X_HCC037_1_036_035_2_035_1_034 | RXC_02 | HCC034, 035_1, 035_2, 036, 037_1 |
| RXC_03_X_HCC142 | RXC_03 | HCC142 |
| RXC_04_X_HCC184_183_187_188 | RXC_04 | HCC183, 184, 187, 188 |
| RXC_05_X_HCC048_041 | RXC_05 | HCC041, 048 |
| RXC_06_X_HCC018_019_020_021 | RXC_06 | HCC018, 019, 020, 021 |
| RXC_07_X_HCC018_019_020_021 | RXC_07 | HCC018, 019, 020, 021 |
| RXC_08_X_HCC118 | RXC_08 | HCC118 |
| RXC_09_X_HCC056 | RXC_09 | HCC056 |
| RXC_09_X_HCC057 | RXC_09 | HCC057 |
| RXC_09_X_HCC048_041 | RXC_09 | HCC041, 048 |
| RXC_10_X_HCC159_158 | RXC_10 | HCC158, 159 |

**Plus the RXC_09 triple intersection:**
```
RXC_09_X_HCC056_057_AND_048_041 = 1
  iff RXC_09 = 1
  AND (HCC056 = 1 OR HCC057 = 1)
  AND (HCC048 = 1 OR HCC041 = 1)
```

This is the only interaction with a triple-AND structure. Easy to miss when implementing from scratch.
</rxc_hcc_interactions>

<scoring_formula>
For each metal level (Platinum, Gold, Silver, Bronze, Catastrophic):
```
SCORE_ADULT_<metal> = Σ (variable_indicator × variable_coefficient_<metal>)
```
Then pick the column matching the enrollee's `METAL`:
```
SCORE_ADULT = SCORE_ADULT_PLATINUM if METAL='P'
            = SCORE_ADULT_GOLD if METAL='G'
            ... (etc.)
```

CSR adjustment:
```
CSR_ADJUSTED_SCORE_ADULT = SCORE_ADULT × RA_Factor(CSR_INDICATOR)
```

See `references/csr-adjustments.md` for the CSR factor table.
</scoring_formula>

<canonical_data>
PY2025 coefficients: `/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/adult_model_factors.csv`

Group mappings: `adult_group_mappings.csv` in the same directory.
Severe list: `severe_list.csv` (column `adult` = 'y').
Transplant list: `transplant_list.csv` (column `adult` = 'y').
RXC interactions: `RXC_interactions.csv`.
RXC hierarchy: `RXC_hierarchy.csv`.
</canonical_data>
