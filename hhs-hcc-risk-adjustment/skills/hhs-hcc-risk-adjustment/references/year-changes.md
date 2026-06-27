<scope>
Year-over-year NBPP changes that affect HHS-HCC model **logic** (not just coefficient updates). Coefficient updates happen every year; logic changes are less frequent and require code changes in implementations. Verified against CMS SAS source for BY2018-BY2024 and the CMS Python release for BY2025.
</scope>

<by2018>
**First V05 release.** Established the modern adult/child/infant tri-model structure.
- Adult severity: legacy single `SEVERE_V3` flag interacting with specific HCCs (HHS_HCC002, 042, 120, 122, 125, 126, 127, 156)
- HCC_ED1-11 (11 month buckets) for partial-year enrollment, NOT contingent on HCC count
- No RXC variables yet
</by2018>

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

<by2023>
**Major revamp of severity model.**
- Old `SEVERE_V3` flag retired
- New `SEVERE_HCC_COUNT*` and `TRANSPLANT_HCC_COUNT*` counters introduced
- HCC_ED collapsed from 11 month buckets to 6 (HCC_ED1-6) AND made HCC-contingent (only fires when `HCC_CNT > 0`)
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
- CSR factor schedule for variants 02 and 03 changed — no longer strictly AV-monotone (see `references/csr-adjustments.md`)
- First Python release alongside SAS (V0825.141.E3)
</by2025>

<long_standing_canonical_rules_easy_to_miss>
These rules have been canonical since at least BY2018 (verified via CMS SAS source) but are easy to miss when porting from incomplete documentation:

1. **HCC064 → SEVERITY4** in infant model: every year BY2018+
2. **HCC028 → SEVERITY2** in infant model: every year BY2018+
3. **AGE0_MALE → AGE1_MALE swap**: when `AGE_LAST=0 AND IHCC_AGE1=1 AND AGE0_MALE=1`, set `AGE0_MALE=0` and `AGE1_MALE=1`. Present in every SAS release BY2018-BY2024 and both DIY tables (BY2024, BY2025). Notably **omitted** from the BY2025 CMS Python release — treat the SAS/DIY tables as canonical.
4. **HHS_HCC022 excluded from HCC_CNT** in Adult and Child models
5. **Pre-grouping and post-grouping HCC checks** for severity/transplant flags — both should trigger
</long_standing_canonical_rules_easy_to_miss>

<canonical_data>
- BY2018-BY2024 SAS source: `/Users/wesley/Documents/CMS HHS-HCC Model/SAS/`
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
