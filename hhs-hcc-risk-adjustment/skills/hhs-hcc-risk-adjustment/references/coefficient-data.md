<scope>
Where canonical HHS-HCC model coefficients live and how to consume them.
</scope>

<canonical_sources>
**For BY2025:**
- Adult coefficients: `data/BY<YYYY>/adult_model_factors.csv`
- Child coefficients: `child_model_factors.csv` (same directory)
- Infant coefficients: `infant_model_factors.csv` (same directory)

**For BY2018-BY2024:**
- The CMS SAS source archive for that benefit year
- Each year's package includes a coefficient table (typically as `.xlsx` or `.TXT`)
- Or extract from the CMS-published "Final HHS Risk Adjustment Model Coefficients" PDFs / Excel files cited on the CMS regulations page

**For the user's local SQL implementation (all years 2022+):**
- `Table-Load-Scripts/dbo.RiskScoreFactors.Table.sql` in the HHS_HCC_SQL repo
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

The `Model_Year` strings in `dbo.RiskScoreFactors`:
- `2022_DIY_122022`
- `2023_NBPP_050622`
- `2024_DIY_090624`
- `2025_DIY_072325`
- `2026_DIY_073126`
- `2027_NBPP_020926`
</file_format>

<loading_in_python>
Use `scripts/load_coefficients.py` (in this skill's `scripts/` folder), or directly:

```python
import pandas as pd

base = "data/BY2026"
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
**Variable naming differences across sources.** The two conventions and how they map:

| Concept | CMS package | DIY tables / SQL |
|---|---|---|
| Adult severity counters | `SEVERE_HCC_COUNT1`-`9`, `10PLUS` | `SEVERE_1_HCC` … `SEVERE_10_HCC` |
| Child severity counters | `SEVERE_HCC_COUNT1`-`5`, `6_7`, `8PLUS` | `SEVERE_1_HCC` … `SEVERE_10_HCC` |
| Adult transplant counters | `TRANSPLANT_HCC_COUNT4`-`7`, `8PLUS` | `TRANSPLANT_4_HCC` … `TRANSPLANT_8_HCC` |
| Child transplant counter | `TRANSPLANT_HCC_COUNT4PLUS` | `TRANSPLANT_4_HCC` … `TRANSPLANT_8_HCC` |
| Enrollment duration | `HCC_ED1`-`6` | `ED_1` … `ED_6` |
| PrEP cost factor | `ACF_PrEP`, `ACF_PrEP_Child` | `ACF_01` |
| RXC interactions | `RXC_01_X_HCC001` | `RXC_01_x_HCC001` (case varies by year) |

Also: BY2018-BY2020 is V05 with different HCC numbering, so `HHS_HCC042` does not necessarily mean the same condition across the V05/V07 boundary.

Do not hand-index a factor dict. Use `scripts/load_coefficients.py:resolve()`, which tries every spelling and the collapsed tier that covers a given count, and returns the name it matched so you can report it.

**Tier aliasing in the DIY layout.** The DIY tables emit one row per count even where counts share a coefficient, so child `SEVERE_6_HCC` and `SEVERE_7_HCC` both carry the single `SEVERE_HCC_COUNT6_7` value. Group-flag rows likewise repeat once per member HCC (BY2027 has three identical `G01` rows and no `HHS_HCC019`/`020`/`021` rows at all). Both are intentional, but **which counts share a tier changes by year** — see the BY2026 child shift in `references/year-changes.md`. Re-derive the tiering from the values each year; never carry last year's assumption forward.

**Zero-coefficient HCCs:**
- HCCs that are part of a Group flag have coefficient 0 in their individual row (e.g., HHS_HCC019, HHS_HCC020, HHS_HCC021 are all 0; G01 carries the value).
- HCC070 and HCC071 are 0 in BY2024 (rolled up to G07A) and have real values in BY2025 (after un-grouping).
</watch_outs>

<bundled_data_provenance>
State of the bundled `data/BY<YYYY>/` tables, as verified against the CMS BY2026 software package and `dbo.RiskScoreFactors`:

| Years | Status |
|---|---|
| BY2018, BY2019 | V05 coefficients. Match `2018_DIY_120418` / `2019_DIY_071619` exactly. |
| BY2020 | V05. Rebuilt from `CY2020 DIY tables 04.13.2021.xlsx` — see below. |
| BY2021-BY2025 | Match `dbo.RiskScoreFactors` exactly |
| BY2026 | Regenerated from the CMS V0826.141.E1 package; matches it exactly |
| BY2027 | Matches `dbo.RiskScoreFactors` (`2027_NBPP_020926`) exactly. Proposed-rule coefficients — draft. |

Two vintages had to be repaired:

**BY2020** was an incomplete extract — the Adult table was missing the first 27 rows of its block (all 18 age/sex variables and `HHS_HCC001`-`011`), a copy-paste offset. Any BY2020 adult score omitted the demographic term entirely. Rebuilt from the CY2020 DIY workbook, whose other 352 rows match the previous content exactly. The same truncation existed upstream in `dbo.RiskScoreFactors` (`2020_DIY_080320`) and has been fixed there too.

**BY2026** previously carried the *proposed* 2026 NBPP (`2026_NBPP_100524`) rather than the final CMS package: most rows off by 0.001-0.008, `ACF_01` off by ~1.06 (adult) and ~0.84 (child), a `HHS_HCC035_1a` typo, a stale `G07A` row, and a one-row shift in the child severity block that gave a child with exactly 7 payment HCCs the `8PLUS` coefficient (16.144) instead of `6_7` (-3.580) — a 19.7-point error. If you have scores computed from the old BY2026 table, they need restating.

`load_factors` now refuses to load any table missing its age/sex block, so this class of truncation fails loudly instead of silently dropping the demographic term.

**Severity model coverage.** `scripts/score_enrollee.py` implements both eras:

| | BY2018-BY2020 | BY2021-BY2022 | BY2023+ |
|---|---|---|---|
| Severity | `SEVERE_V3` → `INT_GROUP_H` / `INT_GROUP_M` | `SEVERE_V3` → `INT_GROUP_H` only | `SEVERE_HCC_COUNT*`, `TRANSPLANT_HCC_COUNT*` |
| Enrollment duration | `ED_1`-`ED_11`, not HCC-contingent | same | `HCC_ED1`-`6`, requires HCC count > 0 |

Verified against the CMS SAS model macros (`V0518F3M.SAS`, `V0519F3M.SAS`, `V0520F5M.SAS`, `CY21M07C.SAS`, `CY22M07C.SAS`). Details in `references/year-changes.md`.
</bundled_data_provenance>
