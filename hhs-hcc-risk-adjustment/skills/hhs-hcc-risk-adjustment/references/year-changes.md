<scope>
Year-over-year NBPP changes that affect HHS-HCC model **logic** (not just coefficient updates). Coefficient updates happen every year; logic changes are less frequent and require code changes in implementations. Verified against CMS SAS source for BY2018-BY2024 and the CMS Python package for BY2026 (V0826.141.E1).
</scope>

<by2018>
**First V05 release.** Established the modern adult/child/infant tri-model structure.
- Adult severity: legacy single `SEVERE_V3` flag interacting with specific HCCs
- `ED_1`-`ED_11` (11 month buckets) for partial-year enrollment, NOT contingent on HCC count
- No RXC variables yet
</by2018>

<pre_2023_severity_model>
The BY2018-BY2022 severity design, verified against the CMS SAS model macros (`V0518F3M.SAS`, `V0519F3M.SAS`, `V0520F5M.SAS`, `CY21M07C.SAS`, `CY22M07C.SAS`). **Adult model only** — the child model of this era has no severity variable.

```
SEVERE_V3 = 1 if any of: HHS_HCC002, 042, 120, 122, 125, 126, 127, 156
                         (unchanged BY2018-BY2022)

INT_GROUP_H = 1 if SEVERE_V3 and any of:
    HHS_HCC006, 008, 009, 010, 115, 135, 145, G08, and
      G06   in BY2018-BY2020   (V05 naming)
      G06A  in BY2021-BY2022   (V07 renaming)

INT_GROUP_M = 1 if INT_GROUP_H = 0 and SEVERE_V3 and any of:
    HHS_HCC035, 038, 153, 154, 163, 253, G03
    -- BY2018-BY2020 ONLY; removed entirely in BY2021
```

Only `INT_GROUP_H` and `INT_GROUP_M` carry coefficients; `SEVERE_V3` and the individual `SEVERE_V3_x_*` products are intermediates. The two groups are mutually exclusive — M is explicitly gated on H being 0.

Three traps when porting this era:
1. **`INT_GROUP_M` vanishes in BY2021.** The macro, the variable, and all seven of its interaction products are dropped. Scoring BY2021+ with an M term invents load that CMS does not pay.
2. **`G06` became `G06A`** in the BY2021 V07 relabeling (alongside G02A→G02B, G07→G07A, G09→G09A/G09C, G15→G15A, G17→G17A, G18→G18A, new G21, and G03 dropped from the adult group set). Matching on the wrong token silently loses `INT_GROUP_H`.
3. **Enrollment duration is not HCC-contingent before BY2023.** `ED_1`-`ED_11` are set purely from `ENROLDURATION = n`, with 12 as the omitted reference category. There is no `ED_12`, and no `SEVERE_HCC_COUNT*` or `TRANSPLANT_HCC_COUNT*` variable exists in any pre-BY2023 year.
</pre_2023_severity_model>

<by2019>
- Coefficient refresh
- No structural logic changes
</by2019>

<by2020>
- Last year of V05 model (V0520.128.Q3)
- Final coefficient refresh under V05
</by2020>

<by2021>
**V07 model launches** (V0721.141.A3).
- HCC count expanded from 128 to 141
- New HCC numbering (e.g., HCC035_1, HCC035_2 splits)
- RXC variables introduced (RXC_01 through RXC_10)
- RXC × HCC interactions introduced
- New infant maturity-by-severity grid structure
</by2021>

<by2022>
- Coefficient refresh
- No structural logic changes
</by2022>

<by2021>
Also in BY2021, as part of the V05 → V07 transition: `INT_GROUP_M` was removed from the adult severity model and the `INT_GROUP_H` group token changed from `G06` to `G06A`. See `pre_2023_severity_model` above.
</by2021>

<by2023>
**Major revamp of severity model.**
- Old `SEVERE_V3` / `INT_GROUP_H` design retired
- New `SEVERE_HCC_COUNT*` and `TRANSPLANT_HCC_COUNT*` counters introduced
- Enrollment duration collapsed from 11 buckets (`ED_1`-`ED_11`) to 6 (`HCC_ED1`-`6`) AND made HCC-contingent (only fires when `HCC_CNT > 0`)
- Modern severe/transplant lists defined
- This is the version most BY2023+ implementations target as the "baseline modern" version
</by2023>

<by2024>
- **G24 group flag added** (Adult only) — collapses HCC018 + HCC183
- G07A group flag still present
- Adult severe list expanded to include G24
- Adult transplant list expanded to include G24
- Coefficient refresh
</by2024>

<by2025>
**Sickle cell disease cost prediction update** (NBPP 2025):

1. **Additional ICD-10 DX codes mapped to CC=71** for sickle cell disease (effective 2025-10-01 per FY2026 ICD-10 cutover):
   - D5720, D57211-D57214, D57218, D57219
   - D5740, D57411-D57414, D57418, D57419
   - D5744, D57451-D57454, D57458
   - These map to CC=71 (sickle cell anemia) for all enrollees

2. **HCC070 and HCC071 ungrouped** in Adult and Child models:
   - G07A group flag **removed** (no longer used in BY2025+)
   - HCC070 now scored individually with its own coefficient
   - HCC071 now scored individually with its own coefficient

3. **HCC070 and HCC071 reassigned in infant model:**
   - HCC070: SEVERITY2 (BY2024) → **SEVERITY3 (BY2025)**
   - HCC071: SEVERITY1 (BY2024) → **SEVERITY2 (BY2025)**

4. **HCC labels updated** to parallel the Medicare Part C V28 reclassification.

**Other BY2025 changes:**
- CSR factor schedule for variants 02 and 03 raised across the board (see `references/csr-adjustments.md`)
- First Python release alongside SAS (V0825.141.E3)
</by2025>

<by2026>
**Additional Cost Factors (ACF) introduced** — the first payment variable driven by drug codes that is neither an RXC nor an HCC:
- `ACF_PrEP` (Adult, `AGE_LAST > 20`, suppressed when `RXC_01 = 1`)
- `ACF_PrEP_Child` (Child, `11 < AGE_LAST < 21`, suppressed when `HHS_HCC001 = 1`)
- New CMS mapping tables `acf_NDC_mappings.csv` and `acf_HCPCS_mappings.csv` (DIY Tables 10c, 10d)
- The DIY tables call both rows `ACF_01`; the CMS package names them separately
- See `references/adult-model.md` for the exclusion logic

**Child severity tier collapsing shifted.** The variable names are unchanged (`SEVERE_HCC_COUNT1`-`5`, `6_7`, `8PLUS`) but which counts share a coefficient moved: in BY2026, counts 1 and 2 collapse to a single value (-11.801 Silver) where BY2024 and BY2025 kept them distinct. The tiering is expressed in the *values*, not the names, so implementations keyed on the CMS names need no change — but anyone reading tiers off the DIY table's one-row-per-count layout must re-derive them each year.

Release tag V0826.141.E1. Model version string in the package is `V0825.141.E1` (`config.py` builds it from a hardcoded `V0825` prefix), which does not match the published `V0826` package name — a cosmetic CMS bug, but it means output filenames say 2025.
</by2026>

<by2027>
Coefficients published with the proposed NBPP (tag `2027_NBPP_020926`); treat as draft until the final notice. No known logic changes versus BY2026.
</by2027>

<long_standing_canonical_rules_easy_to_miss>
These rules have been canonical since at least BY2018 (verified via CMS SAS source) but are easy to miss when porting from incomplete documentation:

1. **HCC064 → SEVERITY4** in infant model: every year BY2018+
2. **HCC028 → SEVERITY2** in infant model: every year BY2018+
3. **AGE0_MALE → AGE1_MALE swap**: when `AGE_LAST=0 AND IHCC_AGE1=1 AND AGE0_MALE=1`, set `AGE0_MALE=0` and `AGE1_MALE=1`. Present in every SAS release BY2018-BY2024, both DIY tables, and the CMS Python package. Note that CMS Python's *output CSV* reports the pre-swap values of these two columns even though the score uses the post-swap ones — see `references/infant-model.md`.
4. **HHS_HCC022 excluded from HCC_CNT** in Adult and Child models
5. **Pre-grouping and post-grouping HCC checks** for severity/transplant flags — both should trigger
</long_standing_canonical_rules_easy_to_miss>

<canonical_data>
- BY2018-BY2024 SAS source (filenames within the CMS SAS archive):
  - `2018-ra-model-sas/V0518F3M.SAS`
  - `hhs-hcc-2019-software.01.17.2020/V0519F3M.SAS`
  - `cy2020-hhs-hcc-sas-software-v0520128q3/V0520F5M.SAS`
  - `hhs-hcc-software-v0721141a3/Unzipped Software/CY21M07C.SAS`
  - `hhs-hcc-software-v0722141b3/CY22M07C.SAS`
  - `hhs-hcc-software-v0723141c4/CY23M07C.SAS`
  - `hhs-hcc-software-v0724141d3/CY24M07C.SAS`
- BY2024 DIY tables: `cy2024-diy-tables-04.09.2025.xlsx`
- BY2025 DIY tables and Python: `CMS Model/cy2025-diy-tables-03.30.2026.xlsx` and `CMS Model/software/HHS_HCC/`
- Source page for older versions: https://www.cms.gov/marketplace/resources/regulations-guidance
</canonical_data>
