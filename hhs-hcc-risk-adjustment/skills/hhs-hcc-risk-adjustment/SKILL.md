---
name: hhs-hcc-risk-adjustment
description: Domain expertise and computational support for the HHS-HCC commercial risk adjustment model (V07, plan years 2018+). Use when the user asks about how the HHS-HCC model works, what the year-over-year NBPP changes are, how to compute a risk score, what a specific coefficient is, or how to compare model specs across plan years. Covers the Adult, Child, and Infant sub-models, CC/HCC hierarchies, severity and transplant counters, RXC interactions, infant maturity-by-severity interactions, and CSR adjustments.
---

<essential_principles>
## How the HHS-HCC Model Works (Always Apply)

The HHS-HCC model is the risk adjustment model for the **commercial individual and small-group ACA markets**. It is published annually by CMS in the Notice of Benefit and Payment Parameters (NBPP) and is **not** the same model as the Medicare CMS-HCC. The model family in use depends on the benefit year — V07 covers BY2021 and onward, V05 covered BY2018-BY2020, and earlier V01-V04 versions covered BY2014-BY2017.

**Always confirm the benefit year before answering substantive questions.** Coefficients, severity placements, group flags, and CSR factors all vary year over year. Never assume a "default" or "current" year; ask the user.

### Principle 1: Three Sub-Models, Not One

Every enrollee is scored under exactly one of three age-based sub-models. The boundary is `AGE_LAST` (age on the last day of the benefit year):

- **Adult model** — `AGE_LAST >= 21`
- **Child model** — `AGE_LAST in [2, 20]`
- **Infant model** — `AGE_LAST in [0, 1]`

The Adult and Child models are HCC-additive. The **Infant model is structurally different** — it does not score HCCs directly; instead it uses a maturity × severity *interaction grid* (see references/infant-model.md). Most cross-version bugs come from confusing infant and child rules.

### Principle 2: HCC Hierarchies Run Before Group Collapsing

Each enrollee's diagnoses map to CCs via `dx_mapping_table` (with effective-date and age/sex edits). CCs become HCCs after applying CC hierarchies (e.g., HCC008 zeros HCC009-013). Adult and Child models then collapse certain HCC pairs/triples into Group flags (G01, G02B, ..., G24). The Infant model does **not** apply group collapsing.

### Principle 3: Severity / Transplant Counters Are Bucket-Schema Specific

The Adult model has 10 severe buckets (1-9, 10PLUS) and 5 transplant buckets (4-7, 8PLUS). The Child model has 7 severe buckets (1-5, **6_7**, **8PLUS**) and a single transplant bucket (**4PLUS**). The Infant model has neither — severity in infants is part of the maturity interaction.

### Principle 4: Year Matters for Both Logic and Data

The published coefficients change every year. The **logic** also changes occasionally (e.g., BY2023 introduced the modern severity model; BY2024 added G24; BY2025 ungrouped HCC070/HCC071 from G07A and reassigned them to higher infant severity for sickle cell disease). Always confirm benefit year before answering or scoring.

### Principle 5: CMS Python ≠ CMS DIY Tables ≠ CMS SAS

CMS publishes the model in three forms — SAS source (canonical, available going back to BY2014), DIY tables (Excel reference workbook, intended for non-SAS implementers), and starting BY2025 a Python package. **The SAS source is the authoritative spec when sources disagree.** A known instance: the BY2025 Python release omits the `AGE0_MALE → AGE1_MALE` reassignment that is present in every SAS release and both the BY2024 and BY2025 DIY tables.

### Principle 6: Diagnoses Only Count from Qualifying Claims

A diagnosis on a claim contributes to risk score **only if** the claim is of a type CMS deems evidence of a clinician-documented condition. Inpatient (UB-04 bill types 111-114, 117) qualifies automatically. Outpatient UB-04 and Professional (CMS-1500) claims qualify only if they carry a CPT/HCPCS code on the CMS qualifying-services list — face-to-face physician encounters, surgical procedures, qualifying telehealth, etc.

**Lab work, DME deliveries, technical-component-only imaging, ambulance transport, and J-code-only claims do not qualify.** A diabetes diagnosis on a lab claim adds nothing to the score, even though the same diagnosis on an office visit would add HCC021. See `references/claim-qualification.md`.

This is the most common source of "I have the diagnosis on a claim, why isn't it scoring?" surprises. RXC variables (Adult only) use a different mechanism — pharmacy NDC matching, no qualifying-claim filter on the pharmacy side.

### Principle 7: Risk Score Is Just One Input to the Transfer

The HHS-HCC model produces a per-enrollee risk score, which aggregates to a Plan Liability Risk Score (PLRS). PLRS is **one component** of the CMS risk transfer formula:

```
T(i) = [PLRS_i · IDF_i · GCF_i / Σ(s · PLRS · IDF · GCF)
        − AV_i · ARF_i · IDF_i · GCF_i / Σ(s · AV · ARF · IDF · GCF)] · P̄_s
```

The transfer also depends on Induced Demand Factor, Geographic Calibration Factor, Actuarial Value, Allowable Rating Factor, and statewide weighted averages. A high risk score does not guarantee a positive transfer, and metal-level decisions for high-risk populations have non-obvious effects. See `references/risk-transfer-formula.md`.
</essential_principles>

<intake>
**Ask the user:**

What would you like to do with the HHS-HCC model?

1. **Explain** — Describe how part of the model works (general principles, a specific sub-model, how a calculation is performed, what changed in a given year)
2. **Calculate score** — Compute a risk score for an enrollee given demographics + flagged HCCs/RXCs
3. **Lookup** — Find a specific coefficient or rule (e.g., "what's the BY2025 Silver coefficient for HHS_HCC042?")
4. **Compare years** — Identify what changed between two plan years
5. **Risk transfer** — Compute or analyze the CMS risk transfer (PLRS, IDF, GCF, AV, ARF) for a plan, or evaluate metal-level optimization

If the user already stated their intent in their request, skip the question and route directly.

**Wait for response unless intent is already clear.**
</intake>

<routing>
| User intent | Workflow |
|---|---|
| 1, "explain", "how does", "what is", "tell me about" | `workflows/explain-model.md` |
| 2, "calculate score", "score an enrollee", "compute risk score" | `workflows/calculate-score.md` |
| 3, "lookup", "find the coefficient", "what's the value of" | `workflows/lookup-coefficient.md` |
| 4, "compare", "what changed", "diff", "year over year" | `workflows/compare-years.md` |
| 5, "transfer", "PLRS", "metal optimization", "IDF", "GCF", "ARF", "AV" | `workflows/risk-transfer.md` |

**After reading the workflow, follow it exactly.**
</routing>

<reference_index>
All domain knowledge in `references/`:

**Architecture and rules:**
- `model-overview.md` — V07 architecture, sub-models, scoring formula, key terminology
- `adult-model.md` — Adult variables, group flags, severity/transplant buckets, HCC_ED, RXC interactions
- `child-model.md` — Child variables, group flags, severity/transplant buckets (note 6_7 and 8PLUS collapsing)
- `infant-model.md` — Maturity hierarchy, severity hierarchy, AGE0/AGE1 swap, maturity × severity grid

**Cross-cutting topics:**
- `claim-qualification.md` — Which medical claims qualify for HCC scoring (inpatient bill types vs outpatient/professional with qualifying CPT/HCPCS), why labs/DME/J-code-only claims don't count, supplemental diagnoses
- `cc-hcc-hierarchies.md` — DX→CC mapping, CC→HCC hierarchies, group collapsing, age/sex/MCE edits
- `rxc-interactions.md` — RXC variables, RXC_06→RXC_07 hierarchy, HCC×RXC interactions including the RXC_09 triple
- `csr-adjustments.md` — CSR adjustment factors by HIOS variant ID, BY2025 schedule change
- `risk-transfer-formula.md` — The full CMS risk transfer formula (PLRS, IDF, GCF, AV, ARF, statewide averages) and metal-level optimization
- `year-changes.md` — Year-over-year NBPP changes (BY2018-BY2027 as available)
- `coefficient-data.md` — Where canonical coefficients live, how to load them

**Local code-mapping CSVs (use Grep to look up specific codes):**
- `dx-mapping.csv` — Full ICD-10 → CC crosswalk (11,568 rows). Columns: `DGNS_CD,CC_CD,ACC_CD,DGNS_CD_EFF_STRT_DT,DGNS_CD_EFF_END_DT,MIN_AGE_DGNS_INCLUDE,MAX_AGE_DGNS_EXCLUDE,CC_AGE_SPLIT_MIN_AGE_INC,CC_AGE_SPLIT_MAX_AGE_EXC,CC_SEX_SPLIT`. Use to answer "what CC does diagnosis X map to?" or "which diagnoses map to HCC Y?" (grep for the CC number in CC_CD column). Includes date-gating and age/sex edit columns.
- `hcpcs-rxc.csv` — HCPCS J-code → RXC mapping (86 rows). Columns: `HCPCS_CODE,RXC`. Use to answer "does this J-code trigger an RXC?" or "which J-codes map to RXC_04?"
- `ndc-rxc.csv` — NDC → RXC pharmacy mapping (15,134 rows). Columns: `NDC_CODE,RXC,start_year,end_year`. Use to answer "does this NDC trigger an RXC?" or "which NDCs map to RXC_05 in BY2025?" (filter by start_year/end_year).
- `service-code-reference.csv` — CPT/HCPCS qualifying-service-code list (21,109 rows). Columns: `SRVC_CD,SRVC_TYPE_CD,SRVC_CD_EFCTV_STRT_DT,SRVC_CD_EFCTV_END_DT,CPT_HCPCSELGBL_RISKADJSTMT_IND`. Use to answer "does CPT code X qualify a claim for risk adjustment?" — look for `CPT_HCPCSELGBL_RISKADJSTMT_IND=Y` with the service date in the effective range. SRVC_TYPE_CD distinguishes CPT (01) from HCPCS (02).

**Bundled reference data in `data/` (loaded automatically by scripts or grepped directly):**
- `data/hcc_labels.csv` — Human-readable label and clinical category for every HCC, group flag, RXC, and interaction variable (210 rows). Columns: `column_name,hcc_number,label,clinical_category`. Use to answer "what does HCC042 mean?" or "which HCCs are in the Oncology category?" — grep by column_name or clinical_category.
- `data/csr_adjustment_factors.csv` — CSR adjustment factors by CSR_Code and model year (BY2020–BY2027, 96 rows). Columns: `CSR_Code,CSR_Desc,model_year,adj_factor`. Loaded automatically by `score_enrollee.py`; also useful for "what is the CSR factor for Silver 94% in BY2025?"
- `data/statewide_ra_factors.csv` — Statewide weighted-average PLRS, IDF, AV, ARF, average premium, and member months by state, market, and year (BY2018–BY2024, ~1,009 rows). Columns: `State,RA_Adj_Avg_Pre,Avg_pre,PLRS,ARF,AV,IDF,MM,Market,Year`. Use to look up the statewide inputs needed for the risk transfer formula — grep by State and Year, then filter by Market (1=Individual, 2=Small Group).
- `data/BY<YYYY>/` — Coefficient CSVs (adult/child/infant model factors) for BY2018–BY2027. Loaded automatically by scripts via `--year`.
</reference_index>

<workflows_index>
| Workflow | Purpose |
|---|---|
| `explain-model.md` | Walk the user through a topic in the model, citing references |
| `calculate-score.md` | Compute a risk score for an enrollee using `scripts/score_enrollee.py` |
| `lookup-coefficient.md` | Find a coefficient by variable name + metal + year using `scripts/lookup.py` |
| `compare-years.md` | Diff model spec across plan years using `references/year-changes.md` |
| `risk-transfer.md` | Compute a CMS risk transfer or analyze metal-level optimization using `scripts/risk_transfer.py` |
</workflows_index>

<scripts_index>
Reusable code in `scripts/`:

- `score_enrollee.py` — End-to-end risk score for one enrollee given demographics + flagged HCCs/RXCs. Reads CMS factor CSVs.
- `load_coefficients.py` — Load CMS adult/child/infant factor CSVs into a dict for lookup or arithmetic.
- `lookup.py` — Quick coefficient lookup by `(model, variable, metal, year)`.
- `risk_transfer.py` — Compute the CMS risk transfer T(i) given PLRS, IDF, GCF, AV, ARF, statewide averages, and average premium. Includes a metal-level inflection-point helper.

Coefficient CSVs for BY2018–BY2027 are bundled in `data/BY<YYYY>/`. Scripts use them automatically via `--year`; pass `--data-dir` to override with a custom path. Always confirm benefit year with the user before scoring — never assume.
</scripts_index>

<key_data_locations>
CMS publishes all model artifacts annually on the CMS website under the Risk Adjustment section. Key file types to obtain for a given benefit year:
- **Coefficient CSVs** — `adult_model_factors.csv`, `child_model_factors.csv`, `infant_model_factors.csv` (from the CMS HHS-HCC software package, inside `data/input/internal/`)
- **SAS source** — canonical logic; available going back to BY2014
- **DIY tables** — Excel reference workbook for non-SAS implementers; published for BY2024 and BY2025
- **DX mapping, HCPCS/NDC crosswalks** — also in the CMS software package; mirrored locally in `references/` CSVs for this skill
</key_data_locations>
