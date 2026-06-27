<scope>
The CSR (Cost-Sharing Reduction) adjustment is a multiplier applied to the risk score for plans where federal CSR programs reduce member cost-sharing below the standard AV. Distinct from the **IDF** in the risk transfer formula — see `references/risk-transfer-formula.md` for that distinction.
</scope>

<csr_pipeline>
Each plan has a `CSR_INDICATOR` derived from the HIOS plan ID suffix (the last two digits of the 16-character plan ID). This indicator maps to an `RA_Factor` (the CSR multiplier). The CSR-adjusted score is:

```
CSR_ADJUSTED_SCORE = SCORE × RA_Factor
```

Applied per-metal and then collapsed by plan METAL the same way the raw score is.
</csr_pipeline>

<csr_indicator_categories>
HIOS plan ID suffixes and what they mean:

| Suffix | Plan type |
|---|---|
| 00 | Catastrophic standard |
| 01 | Standard plan, no CSR (typical Bronze/Silver/Gold/Platinum) |
| 02 | Zero Cost Share (Native American CSR variant) — applies across all metals |
| 03 | Limited Cost Share (Native American CSR variant) — applies across all metals |
| 04 | Standard plan with no CSR (alternate code) |
| 05 | Silver 73% AV (CSR for households 200-250% FPL) |
| 06 | Silver 87% AV (CSR for households 150-200% FPL) |
| 07 | Silver 94% AV (CSR for households 100-150% FPL) |
| 30, 32, 35, 36 | State-subsidy variants — Silver, treated like 06 in PY2025 |
| 31, 34 | Massachusetts Health Connector state-subsidy variants |
| 42 | State-Subsidy Gold (e.g., MA, CT) |
| 43 | State-Subsidy Limited Cost Share Gold |

Some suffixes are state-specific. Variants 31/34 only appear in MA. Variants 42/43 are state-subsidy specific.
</csr_indicator_categories>

<py2025_factor_table>
PY2025 RA_Factor schedule (per CMS PY2025 NBPP, codified in `CSR_table.csv`):

| HIOS Variant | Metal | RA_CSR_Indicator | RA_Factor (PY2025) |
|---|---|---|---|
| 0 | Cat | 1 | 1.00 |
| 1 | Standard | 1 | 1.00 |
| 2 | Platinum (Zero Cost Share) | 4 | **1.51** |
| 2 | Bronze (Zero Cost Share) | 10 | **1.46** |
| 2 | Gold (Zero Cost Share) | 8 | 1.39 |
| 2 | Silver (Zero Cost Share) | 6 | **1.31** |
| 3 | Bronze (Limited Cost Share) | 11 | 1.15 |
| 3 | Silver (Limited Cost Share) | 7 | 1.04 |
| 3 | Gold (Limited Cost Share) | 9 | 1.10 |
| 3 | Platinum (Limited Cost Share) | 5 | **1.19** |
| 4 | Standard | 1 | 1.00 |
| 5, 30-36 | Silver state-subsidy | 3 | 1.12 |
| 42 | State-subsidy Gold | 2 | 1.07 |
| 43 | State-subsidy Limited Cost Share Gold | 9 | 1.10 |

**PY2025 schedule change** (relative to BY2018-BY2024): The Zero Cost Share (variant 02) and Limited Cost Share (variant 03) factors no longer follow a strict AV-monotone pattern. Platinum now gets the largest factor (1.51 / 1.19) and Silver gets the smallest among the major metals (1.31 / 1.04). This was a deliberate CMS recalibration based on observed utilization differences. Implementations carrying forward the BY2018-BY2024 inverted-AV schedule will mis-score variant 02 and 03 for Bronze, Silver, and Platinum metals.
</py2025_factor_table>

<implementation_notes>
**Two distinct numbering schemes:**
- The raw HIOS suffix (literal characters at end of plan ID, e.g., "02", "06")
- The CMS-internal `RA_CSR_Indicator` (numeric, e.g., 4 = "zero-cost-share Platinum")

These are not the same. The user's SQL implementation uses its own internal `csr_code` numbering yet again. As long as the suffix → multiplier pipeline yields the right RA_Factor, the intermediate numbering doesn't matter functionally.

**Rule of thumb:** when comparing implementations, verify the HIOS suffix → RA_Factor end-to-end, not the intermediate codes.

**Standalone catastrophic plans:** suffix 00, factor 1.00. Catastrophic plans are not eligible for CSR.

**Multi-CSR enrollment:** an enrollee may have one CSR variant for part of the year and another for the rest (income changes). Each enrollment span carries its own CSR_INDICATOR; the score is computed per span and weighted by member-months.
</implementation_notes>

<canonical_data>
Bundled in this repo: `data/csr_adjustment_factors.csv` — CSR_Code (Evensun internal numbering) → adj_factor by model_year (BY2020–BY2027). **Note:** CSR_Code in this CSV uses a different numbering than the RA_CSR_Indicator used by `score_enrollee.py --csr`. See `implementation_notes` above. Useful for cross-referencing by CSR description or csr_lds suffix.

CMS canonical source: the `CSR_table.csv` published in the annual HHS-HCC software package (`data/input/internal/`), and the `CSR` macro in the CMS SAS source (`CY##M07C.SAS` for V07, `V05##F#M.SAS` for V05).
</canonical_data>
