# Workflow: Compare HHS-HCC Model Spec Across Plan Years

<required_reading>
1. `references/year-changes.md` — known logic-level changes by benefit year
2. `references/coefficient-data.md` — where coefficients live for each year
</required_reading>

<process>
## Step 1: Identify the two (or more) years

Ask the user which years to compare. Common comparisons:
- BY{N-1} vs BY{N} — what changed in the new year
- BY{N} as implemented in production vs BY{N+1} as drafted in NBPP
- BY2020 (V05) vs BY2021 (V07) — major version change

## Step 2: Distinguish logic vs coefficient changes

**Logic changes** (require code updates):
- Group flag additions/removals (e.g., G24 added BY2024, G07A removed BY2025)
- Severity bucket schema changes (e.g., HCC_ED schema BY2022→BY2023)
- HCC severity placements (e.g., HCC070/HCC071 moved BY2024→BY2025)
- New HCCs added or HCCs removed (e.g., V05→V07 transition)
- New ICD-10 DX codes mapped to existing CCs (date-gated, but still affects scores)
- AGE0_MALE/AGE1_MALE swap and similar special rules

**Coefficient changes** (data-only):
- Every variable's coefficient changes every year
- Compare via `RiskScoreFactors` table or CMS CSV diffs
- Don't enumerate every coefficient delta — focus on directional shifts (e.g., "demographic factors decreased ~5% across the board" or "RXC_10 coefficient increased 15%")

## Step 3: Read the year-changes reference

`references/year-changes.md` has the curated logic-change list. Read the sections for both years (and any years in between) and compile the diff.

## Step 4: For deeper diff — go to the SAS source

For changes not captured in the reference:
- BY2018-BY2024 SAS source: `/Users/wesley/Documents/CMS HHS-HCC Model/SAS/`
- Each year's `CY##M07C.SAS` (V07) or `V0##F#M.SAS` (V05) is the canonical implementation
- Diff structurally relevant macros across years (e.g., `IHCC_SEVERITY_LIST`, severity assignment block, group flag block)

Useful one-liners:
```bash
# Compare severity assignment between two years
diff "/Users/wesley/Documents/CMS HHS-HCC Model/SAS/hhs-hcc-software-v0723141c4/CY23M07C.SAS" \
     "/Users/wesley/Documents/CMS HHS-HCC Model/SAS/hhs-hcc-software-v0724141d3/CY24M07C.SAS"
```

## Step 5: For coefficient comparison

Use the user's `RiskScoreFactors` table:
```sql
SELECT a.Variable, a.Silver_Level AS BY{N-1}_Silver, b.Silver_Level AS BY{N}_Silver,
       (b.Silver_Level - a.Silver_Level) AS delta,
       (b.Silver_Level - a.Silver_Level) / NULLIF(a.Silver_Level, 0) AS pct_change
FROM RiskScoreFactors a
JOIN RiskScoreFactors b ON a.Model = b.Model AND a.Variable = b.Variable
WHERE a.Model_Year = '2024_DIY_090624' AND b.Model_Year = '2025_DIY_072325'
ORDER BY ABS(pct_change) DESC;
```

## Step 6: Report

Summarize:
- Logic changes (the meaningful ones — usually 1-3 per year for incremental updates, or 5-10 for V05→V07 jumps)
- Coefficient direction (increased / decreased / mixed) and any extreme outliers
- Implementation impact: do existing implementations need code changes?
</process>

<success_criteria>
This workflow is complete when:
- [ ] Both years confirmed
- [ ] Logic changes enumerated with source citations (CMS SAS line refs or NBPP language)
- [ ] Coefficient direction characterized
- [ ] Implementation impact called out (code changes required vs data-only refresh)
</success_criteria>
