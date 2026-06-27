# Workflow: Look Up a Coefficient

<required_reading>
1. `references/coefficient-data.md` — file locations, format, naming conventions
</required_reading>

<process>
## Step 1: Confirm benefit year and sub-model

**Always ask the user explicitly:**
- Which benefit year (e.g., BY2023, BY2024, BY2025)?
- Which sub-model (Adult / Child / Infant)?

Coefficients are model-year × sub-model × variable × metal-level. All four are required.

## Step 2: Identify the variable name

The user may say:
- "HCC042" or "HHS_HCC042" → variable name `HHS_HCC042`
- "diabetes severe" → ask for the HCC number (HCC019/020/021 family) or look up in the description column
- "65 year old male" → variable `MAGE_LAST_60_GT`
- "G24" → variable `G24` (Adult only)
- "the platinum infant immature severity 4 coefficient" → variable `IMMATURE_X_SEVERITY4`, metal Platinum

## Step 3: Run the lookup

```bash
python3 /Users/wesley/.claude/skills/hhs-hcc-risk-adjustment/scripts/lookup.py \
  --year 2025 --model Adult --variable HHS_HCC042 --metal Silver
```

Or to get all metals at once, omit `--metal`:
```bash
python3 /Users/wesley/.claude/skills/hhs-hcc-risk-adjustment/scripts/lookup.py \
  --year 2025 --model Adult --variable HHS_HCC042
```

For BY2025, the script reads from CMS-published CSVs. For other years, the script falls back to the user's local SQL `RiskScoreFactors` extract if available, or reports that the year isn't loaded.

## Step 4: Cross-check sources

If the answer matters (e.g., for an audit), cross-check between the CMS CSV (canonical) and the user's SQL `RiskScoreFactors` table to confirm they match for that benefit year.
</process>

<success_criteria>
This workflow is complete when:
- [ ] Year, sub-model, variable, and metal are all confirmed
- [ ] The coefficient value is returned
- [ ] If multiple sources were available, they were cross-checked
</success_criteria>
