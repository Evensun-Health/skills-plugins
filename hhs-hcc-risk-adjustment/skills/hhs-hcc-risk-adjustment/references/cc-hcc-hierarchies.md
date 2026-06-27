<scope>
How diagnoses become CCs become HCCs become Group flags. Applies across all sub-models (with sub-model-specific group collapsing).

**Upstream prerequisite:** Diagnoses considered for the DX→CC pipeline must come from a **qualifying claim**. Inpatient (UB-04 bill types 111-114, 117) auto-qualifies; outpatient UB and professional claims require a CPT/HCPCS on the CMS qualifying-services list. Lab work, DME, technical-component imaging, ambulance, and J-code-only claims are filtered out before this stage. See `references/claim-qualification.md`.
</scope>

<dx_to_cc>
Each ICD-10 diagnosis code maps to zero, one, or two CCs through a `dx_mapping_table` (CMS-published; in the user's SQL implementation it's `dbo.DX_Mapping_Table`). The full crosswalk is available locally at `references/dx-mapping.csv` (11,568 rows) — use Grep to look up specific diagnosis codes or CC numbers.

A typical mapping row has:
- `DGNS_CD` — the ICD-10 code (e.g., `Q390`)
- `DGNS_CD_EFF_STRT_DT` / `DGNS_CD_EFF_END_DT` — diagnosis date validity window (often aligned to FY ICD-10 cutovers, e.g., October 1)
- `MIN_AGE_DGNS_INCLUDE` / `MAX_AGE_DGNS_EXCLUDE` — patient age bounds for the code to be valid (MCE edits)
- `CC_AGE_SPLIT_MIN_AGE_INC` / `CC_AGE_SPLIT_MAX_AGE_EXC` — RTI age splits (e.g., HCC008 vs HCC009 by age 18)
- `CC_SEX_SPLIT` — `'X'`, `'male'`, or `'female'`
- `CC_CD` — primary CC assignment
- `ACC_CD` — secondary CC assignment (rare; used for codes that map to multiple CCs)

A diagnosis must satisfy all gates (date, age, sex, MCE) for the CC to flag. An ICD-10 outside its effective date window contributes nothing — this is how new codes (e.g., FY2026 sickle cell codes effective 2025-10-01) are gated cleanly without year-specific code branching.
</dx_to_cc>

<cc_to_hcc_hierarchy>
After all CC flags are set, **CC hierarchies** zero out lower-priority CCs when a higher-priority CC is present in the same disease family. Examples:

```
HCC003 = 1 → HCC004 = 0
HCC008 = 1 → HCC009 = 0, HCC010 = 0, HCC011 = 0, HCC012 = 0, HCC013 = 0
HCC009 = 1 → HCC010 = 0, HCC011 = 0, HCC012 = 0, HCC013 = 0
...
```

The hierarchy is published in CMS Table 4 ("V07 HHS-HCC Hierarchies") and codified in the CMS data file `HCC_hierarchy.csv` (`/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/HCC_hierarchy.csv`).

The output of this stage is HCCs (with the `HHS_HCC` prefix in the CMS spec).
</cc_to_hcc_hierarchy>

<group_collapsing>
**Adult and Child only.** After CC hierarchies, certain HCC sets collapse into Group flags:

```
G01 = HCC019 OR HCC020 OR HCC021     (then zero HCC019, HCC020, HCC021)
G14 = HCC128 OR HCC129               (then zero both)
... etc.
```

Group sets differ between Adult and Child — see `references/adult-model.md` and `references/child-model.md`. The Infant model does NOT collapse.

**Year sensitivity:** Group sets evolve. Notable changes:
- BY2024: G24 added (collapses HCC018, HCC183 in Adult only)
- BY2025: G07A removed (HCC070, HCC071 ungrouped in both Adult and Child)

When implementing, gate group creation on `benefit_year` to preserve historical accuracy across reruns.
</group_collapsing>

<age_sex_edits>
Age and sex edits gate whether a diagnosis maps to a CC at all:

**MCE age edits:**
- Use `AGE_AT_DIAGNOSIS` (age on the date of service), not `AGE_LAST`
- E.g., a maternity code on a 65-year-old is invalid — CC won't flag

**RTI age splits:**
- Use `AGE_LAST` (age at end of enrollment year)
- E.g., HCC008 (Acute Lymphoid Leukemia 18+) vs HCC009 (Acute Lymphoid Leukemia <18)

**Sex edits:**
- A code restricted to `'female'` (e.g., pregnancy) won't map for `SEX = 'M'`

The `switch_edits` parameter in CMS Python controls whether MCE edits are enforced. Default is True; turn off only for special analyses.
</age_sex_edits>

<example_walk_through>
**Example:** A 25-year-old woman with diagnosis `Q390` (Esophageal atresia without fistula) on 2025-08-15.

1. **DX → CC:** Look up Q390 in `dx_mapping_table`. Row: `Q390 → CC=64`, valid 2015-10-01 to 2027-12-31, age 0-2 (CC_AGE_SPLIT_MAX_AGE_EXC=2). The diagnosis date 2025-08-15 is in window, but the patient is 25 (not <2) → **CC=64 does not flag** for this person (RTI age split fails).

2. Same code on a 6-month-old infant: Row applies, CC=64 flags.

3. **CC → HCC:** CC=64 → HCC064 (1:1 in V07).

4. **Group collapsing:** HCC064 is not part of any group → stays HCC064.

5. **Severity (infant):** HCC064 → IHCC_SEVERITY4 (per `infant_severity_mappings.csv`).

6. **Final:** Infant gets SEVERITY4 + their maturity → one of the X_SEVERITY4 interaction flags fires.
</example_walk_through>

<canonical_data>
- DX → CC mapping: `references/dx-mapping.csv` (local, 11,568 rows). Also published as Table 3 of the CMS DIY tables and as `ICD10_HHS_CC_mappings_<fiscal_year>.csv` in the CMS Python release.
- CC → HCC hierarchy: `HCC_hierarchy.csv`, also Table 4 of the DIY tables.
- MCE age edits: `MCE_AGE_CONDITION` column in the ICD-10 mapping; logic codified in `software/HHS_HCC/utils.py`.
- Group mappings: `adult_group_mappings.csv` / `child_group_mappings.csv`.
</canonical_data>
