<scope>
RXC variables and RXC × HCC interactions. **Adult model only** — Child and Infant models do not use RXCs.
</scope>

<rxc_variables>
10 prescription drug categories: `RXC_01` through `RXC_10`. Each represents a class of drugs / clinical condition where pharmacy or clinician-administered drug data adds predictive value beyond diagnosis-based HCCs.

| RXC | Clinical category (informal) |
|---|---|
| RXC_01 | HIV / antiretrovirals |
| RXC_02 | Multiple sclerosis / immunomodulators (overlaps with HCC034 family) |
| RXC_03 | Hepatitis C antivirals |
| RXC_04 | Cystic fibrosis modulators |
| RXC_05 | Diabetes — insulin and analogs |
| RXC_06 | Transplant immunosuppressants — primary |
| RXC_07 | Transplant immunosuppressants — secondary |
| RXC_08 | ESRD / dialysis-related |
| RXC_09 | Diabetes — non-insulin specialty agents |
| RXC_10 | Hemophilia clotting factors |

These category labels are illustrative for understanding scope; the canonical mappings are available locally:

**Source data (local CSVs — use Grep to look up specific codes):**
- NDC codes from pharmacy claims → `references/ndc-rxc.csv` (15,134 rows: `NDC_CODE,RXC,start_year,end_year`). Filter by `start_year`/`end_year` to match the benefit year.
- HCPCS codes from medical claims → `references/hcpcs-rxc.csv` (86 rows: `HCPCS_CODE,RXC`). Clinician-administered drugs (J-codes, Q-codes).
- Effective on a service date and paid through the CMS-specified deadline
</rxc_variables>

<rxc_hierarchy>
Only one rule (in PY2025): `RXC_06 = 1 → RXC_07 = 0`.

This reflects clinical hierarchy where RXC_06 represents the more potent/primary transplant regimen and RXC_07 the secondary or alternative. An enrollee on both gets credit only for RXC_06.

Codified in `RXC_hierarchy.csv`:
```
RXC,Secondary_RXC
6,7.0
```
</rxc_hierarchy>

<rxc_hcc_interactions>
RXC × HCC interaction flags fire when both an RXC and at least one of a specified HCC list are present. The interactions:

| Interaction variable | RXC | HCC list (any one fires) |
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

Interactions are inclusive — an enrollee can fire multiple if they qualify (e.g., RXC_09 with HCC056 and HCC048 fires both `RXC_09_X_HCC056` and `RXC_09_X_HCC048_041`).
</rxc_hcc_interactions>

<rxc_09_triple_interaction>
**Special case** — only triple-AND interaction in the model:

```
RXC_09_X_HCC056_057_AND_048_041 = 1
  iff
    RXC_09 = 1
  AND (HCC056 = 1 OR HCC057 = 1)
  AND (HCC048 = 1 OR HCC041 = 1)
```

This represents diabetic complications combined with severe heart/vascular disease while on diabetes specialty agents. Has a positive coefficient (additional risk on top of the individual RXC_09 × HCC interactions).

This interaction is easy to miss because the data file `RXC_interactions.csv` represents it as a row that's actually three rows in disguise (or hand-coded in the SAS/Python source). In CMS Python, it's hardcoded in `software/HHS_HCC/utils.py`:

```python
adult_model_df['RXC_09_X_HCC056_057_AND_048_041'] = (
    (adult_model_df['RXC_09'] == 1) &
    ((adult_model_df['HHS_HCC056'] == 1) | (adult_model_df['HHS_HCC057'] == 1)) &
    ((adult_model_df['HHS_HCC048'] == 1) | (adult_model_df['HHS_HCC041'] == 1))
).astype(int)
```

The user's SQL implementation hand-codes it the same way at line ~1712 of the DIY Model Script.
</rxc_09_triple_interaction>

<pre_post_grouping>
Whether RXC × HCC interactions check pre-grouping or post-grouping HCCs varies by implementation:
- CMS Python: checks **either** pre-grouping or post-grouping HCC values
- User's SQL: checks post-grouping only

In practice, none of the HCCs that appear in RXC interaction lists are members of any group (e.g., HCC001, HCC034 family, HCC142, HCC183/184/187/188, HCC041/048, HCC018-021, HCC056/057, HCC118, HCC158/159, HCC037_1). So the distinction never bites.
</pre_post_grouping>

<canonical_data>
- RXC interactions: `/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/RXC_interactions.csv`
- RXC hierarchy: `RXC_hierarchy.csv`
- NDC → RXC mapping: `references/ndc-rxc.csv` (local, 15,134 rows with year ranges)
- HCPCS → RXC mapping: `references/hcpcs-rxc.csv` (local, 86 rows)
- Coefficients: `adult_model_factors.csv` (look for rows starting with `RXC_*`)
</canonical_data>
