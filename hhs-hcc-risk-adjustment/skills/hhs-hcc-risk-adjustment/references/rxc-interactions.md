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
Only one rule (unchanged through BY2026): `RXC_06 = 1 → RXC_07 = 0`.

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

This interaction is easy to miss because it has **no row** in `RXC_interactions.csv` — that file's schema is one RXC plus a flat list of HCCs, which cannot express a conjunction of two HCC groups. It is hardcoded instead. In CMS Python, in `software/HHS_HCC/utils.py`:

```python
adult_model_df['RXC_09_X_HCC056_057_AND_048_041'] = (
    (adult_model_df['RXC_09'] == 1) &
    ((adult_model_df['HHS_HCC056'] == 1) | (adult_model_df['HHS_HCC057'] == 1)) &
    ((adult_model_df['HHS_HCC048'] == 1) | (adult_model_df['HHS_HCC041'] == 1))
).astype(int)
```

The SQL DIY script hand-codes it the same way, alongside the other RXC interaction updates.
</rxc_09_triple_interaction>

<pre_post_grouping>
**The interactions must be evaluated against pre-grouping HCCs.** Several HCCs in the interaction lists are group members, so a post-grouping-only check silently loses the interaction:

| Interaction HCC | Absorbed into | Model |
|---|---|---|
| HCC019, HCC020, HCC021 | G01 | Adult and Child |
| HCC018, HCC183 | G24 | Adult (BY2024+) |
| HCC187, HCC188 | G16 | Adult and Child |

This affects `RXC_04_X_HCC184_183_187_188`, `RXC_06_X_HCC018_019_020_021`, and `RXC_07_X_HCC018_019_020_021`.

How each implementation handles it:
- **CMS Python** tests both the pre-grouping and post-grouping frames (`has_any_hcc(adult_model_df, ...) | has_any_hcc(adult_model_df_pre_grouping, ...)` in `create_adult_model_vars`).
- **The SQL DIY script** applies the RXC interaction updates *before* the group-collapsing updates, so it reads pre-grouping values and gets the same answer.
- **`scripts/score_enrollee.py`** takes post-grouping input, so it expands each group flag back to its member HCCs (`expand_groups`) before testing membership.

Worked example, verified against the CMS BY2026 software: an adult with RXC_06 and only HCC019 collapses to `G01=1, HCC019=0`. CMS still fires `RXC_06_X_HCC018_019_020_021`. A post-grouping-only check drops it and understates the BY2026 Silver score by 0.499.
</pre_post_grouping>

<canonical_data>
- NDC → RXC mapping: `references/ndc-rxc.csv` (local, 15,134 rows with year ranges)
- HCPCS → RXC mapping: `references/hcpcs-rxc.csv` (local, 86 rows)
- Coefficients: `data/BY<YYYY>/adult_model_factors.csv` (rows starting with `RXC_`)

In the CMS software package, the interaction definitions live in
`software/HHS_HCC/data/input/internal/RXC_interactions.csv` and the hierarchy in
`RXC_hierarchy.csv` alongside it.

**Naming across years:** the bundled coefficient tables spell the interaction rows
`RXC_01_X_HCC001` in some years and `RXC_01_x_HCC001` in others, and the CMS
package differs from the DIY tables on the severity and enrollment-duration rows.
`scripts/load_coefficients.py:resolve()` reconciles the spellings — look variables
up through it rather than indexing the dict directly.
</canonical_data>
