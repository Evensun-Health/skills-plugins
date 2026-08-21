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
HIOS plan ID variant suffixes and what they mean (per the CMS BY2026 software writeup, Section IV):

| Suffix | Plan type |
|---|---|
| 00 | Non-CSR / unknown CSR |
| 01 | Standard plan, no CSR (typical Bronze/Silver/Gold/Platinum) |
| 02 | Zero Cost Sharing plan variation — applies across all metals |
| 03 | Limited Cost Sharing plan variation — applies across all metals |
| 04 | Silver 73% AV plan variation (CSR for households 200-250% FPL) |
| 05 | Silver 87% AV plan variation (CSR for households 150-200% FPL) |
| 06 | Silver 94% AV plan variation (CSR for households 100-150% FPL) |
| 30 | State-subsidy off-exchange Silver (~73% AV) |
| 31, 34 | State-subsidy Silver — 73-86% AV, or 94% AV in Massachusetts |
| 32, 35, 36 | State-subsidy Silver — 87-100% AV |
| 42 | State-subsidy Gold (90-100% AV) |
| 43 | State-subsidy Limited Cost Sharing Gold |

There is **no suffix 07**. The three standard CSR Silver variations are 04 (73%), 05 (87%), and 06 (94%) — an off-by-one here is a common porting error, since 73/87/94 reads naturally as 05/06/07.

Suffixes 31 and 34 are the awkward ones: they map to indicator 1 for the 73-86% AV band and to indicator 3 for the 94% AV Massachusetts band. Same suffix, two different factors, resolved by state and AV. The bundled `CSR_table.csv` lists only the indicator-3 rows for 31/34, so a lookup keyed purely on suffix will over-adjust the 73-86% AV plans.
</csr_indicator_categories>

<factor_table>
BY2025+ RA_Factor schedule, verified against `CSR_table.csv` in the CMS BY2026 software package:

| HIOS Variant | Metal | RA_CSR_Indicator | RA_Factor |
|---|---|---|---|
| 00, 01, 04, 30, 31, 34 | any / Silver | 1 | 1.00 |
| 42 | Gold (state subsidy) | 2 | 1.07 |
| 05, 06, 31, 32, 34, 35, 36 | Silver (87-100% AV) | 3 | 1.12 |
| 02 | **Bronze** (Zero Cost Sharing) | 4 | **1.51** |
| 03 | **Bronze** (Limited Cost Sharing) | 5 | **1.19** |
| 02 | **Platinum** (Zero Cost Sharing) | 6 | **1.31** |
| 03 | **Platinum** (Limited Cost Sharing) | 7 | **1.04** |
| 02 | Gold (Zero Cost Sharing) | 8 | 1.39 |
| 03 | Gold (Limited Cost Sharing) | 9 | 1.10 |
| 43 | Gold (state subsidy) | 9 | 1.10 |
| 02 | Silver (Zero Cost Sharing) | 10 | 1.46 |
| 03 | Silver (Limited Cost Sharing) | 11 | 1.15 |

**Read the indicator numbering carefully — it is not ordered by metal.** The sequence runs Bronze, Bronze, Platinum, Platinum, Gold, Gold, Silver, Silver (4-11), alternating Zero and Limited Cost Sharing. Indicator 4 is Bronze, not Platinum.

**The factors are monotone decreasing in AV**, which is the intuitive direction: the Zero Cost Sharing variation drops member cost sharing to zero, so it lifts plan liability most for the metal that started with the least generous cost sharing.

- Zero Cost Sharing: Bronze 1.51 > Silver 1.46 > Gold 1.39 > Platinum 1.31
- Limited Cost Sharing: Bronze 1.19 > Silver 1.15 > Gold 1.10 > Platinum 1.04

**BY2025 schedule change** (relative to BY2018-BY2024): the Zero and Limited Cost Sharing factors were all raised. The pre-BY2025 schedule was Zero Cost Sharing Bronze 1.15 / Silver 1.12 / Gold 1.07 / Platinum 1.00 and Limited Cost Sharing Bronze 1.15 / Silver 1.12 / Gold 1.07 / Platinum 1.00. An implementation carrying the old schedule forward under-adjusts every variant 02 and 03 enrollee — by 0.36 on Zero Cost Sharing Bronze, the largest single gap.
</factor_table>

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

`scripts/score_enrollee.py` carries the RA_CSR_Indicator schedule inline. Its BY2025+ row is verified against the CMS BY2026 `CSR_table.csv`; its BY2018-BY2024 row is reconstructed from that era's published per-metal factors and should be confirmed against the relevant year's own `CSR_table.csv` before use in a restatement.

CMS canonical source: the `CSR_table.csv` published in the annual HHS-HCC software package (`software/HHS_HCC/data/input/internal/`), the plan-variation table and `CSR_INDICATOR` value list in the software description PDF (Section IV), and the `CSR` macro in the CMS SAS source (`CY##M07C.SAS` for V07, `V05##F#M.SAS` for V05).
</canonical_data>
