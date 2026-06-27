<scope>
Where canonical HHS-HCC model coefficients live and how to consume them.
</scope>

<canonical_sources>
**For BY2025:**
- Adult coefficients: `/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal/adult_model_factors.csv`
- Child coefficients: `child_model_factors.csv` (same directory)
- Infant coefficients: `infant_model_factors.csv` (same directory)

**For BY2018-BY2024:**
- SAS source archive at `/Users/wesley/Documents/CMS HHS-HCC Model/SAS/`
- Each year's package includes a coefficient table (typically as `.xlsx` or `.TXT`)
- Or extract from the CMS-published "Final HHS Risk Adjustment Model Coefficients" PDFs / Excel files cited on the CMS regulations page

**For the user's local SQL implementation (all years 2022+):**
- `/Users/wesley/Documents/GitHub/HHS_HCC_SQL/Table-Load-Scripts/dbo.RiskScoreFactors.Table.sql`
- Loaded into table `dbo.RiskScoreFactors` keyed by `(Model, Variable, Model_Year)`
</canonical_sources>

<file_format>
**CMS CSV format** (`adult_model_factors.csv` etc.):
```
Variable,Platinum Level,Gold Level,Silver Level,Bronze Level,Catastrophic Level
MAGE_LAST_21_24,0.189,0.128,0.086,0.057,0.056
HHS_HCC001,0.342,0.265,0.234,0.197,0.196
HHS_HCC002,9.075,8.875,8.83,8.74,8.739
...
```

One row per variable. Five coefficient columns (one per metal). Variables include:
- Age/sex bins
- HCCs
- Group flags (Adult/Child)
- Severe / Transplant counters (Adult/Child)
- HCC_ED1-6 (Adult)
- RXCs and RXC × HCC interactions (Adult)
- Maturity × Severity interactions (Infant)
- AGE0_MALE, AGE1_MALE (Infant)

**SQL table format** (RiskScoreFactors):
```
Model           Variable        Platinum_Level  Gold_Level  Silver_Level  Bronze_Level  Catastrophic_Level  Model_Year
Adult           MAGE_LAST_21_24 0.189           0.128       0.086         0.057         0.056               2025_DIY_072325
Adult           HHS_HCC001      0.342           0.265       0.234         0.197         0.196               2025_DIY_072325
...
```

The user's `Model_Year` strings:
- `2022_DIY_122022`
- `2023_NBPP_050622`
- `2024_DIY_090624`
- `2025_DIY_072325`
- `2026_NBPP_100524`
- `2027_NBPP_020926`
</file_format>

<loading_in_python>
Use `scripts/load_coefficients.py` (in this skill's `scripts/` folder), or directly:

```python
import pandas as pd

base = "/Users/wesley/Documents/CMS HHS-HCC Model/CMS Model/software/HHS_HCC/data/input/internal"
adult = pd.read_csv(f"{base}/adult_model_factors.csv").set_index("Variable")
# adult.loc["HHS_HCC042", "Silver Level"] -> 10.903
```
</loading_in_python>

<loading_in_sql>
```sql
SELECT Variable, Platinum_Level, Gold_Level, Silver_Level, Bronze_Level, Catastrophic_Level
FROM dbo.RiskScoreFactors
WHERE Model = 'Adult'
  AND Model_Year = '2025_DIY_072325'
  AND Variable = 'HHS_HCC042';
```
</loading_in_sql>

<watch_outs>
**Variable naming differences across sources:**
- CMS Python uses `HHS_HCC042`
- CMS DIY tables use `HHS_HCC042` or `HHS HCC042` (with space)
- User's SQL uses `HHS_HCC042` (in `RiskScoreFactors`) but `HHS_HCC042` as a column name in `hcc_list`
- BY2018-BY2020 used different HCC numbering — `HHS_HCC042` may not map across the V05/V07 boundary

**Bucket aliasing in user's SQL:**
- The CMS model uses `SEVERE_HCC_COUNT6_7` (one bucket) for child, but the user's SQL has separate `SEVERE_6_HCC` and `SEVERE_7_HCC` rows in `RiskScoreFactors` — both with the same coefficient. Same for `SEVERE_8_HCC` / `SEVERE_9_HCC` / `SEVERE_10_HCC` (all = `SEVERE_HCC_COUNT8PLUS`) and `TRANSPLANT_4_HCC` through `TRANSPLANT_8_HCC` (all = `TRANSPLANT_HCC_COUNT4PLUS`).
- This aliasing is correct and intentional — when comparing implementations, sum or compare aliased rows together.

**Zero-coefficient HCCs:**
- HCCs that are part of a Group flag have coefficient 0 in their individual row (e.g., HHS_HCC019, HHS_HCC020, HHS_HCC021 are all 0; G01 carries the value).
- HCC070 and HCC071 are 0 in BY2024 (rolled up to G07A) and have real values in BY2025 (after un-grouping).
</watch_outs>
