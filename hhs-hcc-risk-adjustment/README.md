# HHS-HCC Risk Adjustment — Claude Code Skill

A [Claude Code](https://claude.ai/code) skill providing domain expertise and computational tools for the **HHS-HCC commercial risk adjustment model** (V07, plan years 2018+) used in the ACA Individual and Small Group markets.

## What this skill does

When installed, this skill gives Claude deep knowledge of the HHS-HCC model and the ability to:

- **Explain** how the model works — sub-models, HCC hierarchies, severity/transplant counters, RXC interactions, infant maturity×severity grids, qualifying-claim rules, and more
- **Calculate risk scores** for enrollees given demographics and flagged HCCs/RXCs
- **Look up coefficients** by variable, metal level, and benefit year
- **Compare plan years** — what changed in the NBPP year over year (BY2018–BY2027)
- **Compute risk transfers** — PLRS, IDF, GCF, AV, ARF, statewide averages, and metal-level inflection-point analysis

## Bundled data

Coefficient CSVs for **BY2018–BY2027** are included in `data/BY<YYYY>/`:

| Folder | Source revision | Notes |
|--------|----------------|-------|
| BY2018 | `2018_DIY_120418` | V05 |
| BY2019 | `2019_DIY_041520` | V05 |
| BY2020 | `2020_DIY_080320` | V05 |
| BY2021 | `2021_DIY_033122` | V07 (first V07 year) |
| BY2022 | `2022_DIY_122022` | V07 |
| BY2023 | `2023_NBPP_050622` | V07 |
| BY2024 | `2024_DIY_090624` | V07 |
| BY2025 | `2025_DIY_072325` | V07 |
| BY2026 | `2026_NBPP_100524` | V07 |
| BY2027 | `2027_NBPP_020926` | V07 |

DIY revisions supersede the initial NBPP release for a given year when both exist. All data sourced from CMS-published materials.

## Scripts

Python 3.10+ scripts in `scripts/` (stdlib only, no dependencies):

```bash
# Score an enrollee
python3 scripts/score_enrollee.py --age 45 --sex F --metal S --csr 1 --year 2025 \
    --hcc HHS_HCC042 HHS_HCC156 --rxc RXC_09 --enrol-duration 12

# Look up a coefficient
python3 scripts/lookup.py --year 2025 --model Adult --variable HHS_HCC042 --metal Silver

# Compute a risk transfer
python3 scripts/risk_transfer.py --plrs 1.8 --idf 1.08 --gcf 1.09 --av 0.8 --arf 1.90 \
    --statewide-plrs 1.5 --statewide-idf 1.03 --statewide-gcf 1.0 \
    --statewide-av 0.686 --statewide-arf 1.541 --premium 375
```

The `--year` flag selects the bundled coefficient set. Pass `--data-dir` to override with a custom path.

## Installing the skill

Add to your `.claude/settings.json` (or the equivalent project settings):

```json
{
  "skills": [
    {
      "path": "/path/to/hhs-hcc-risk-adjustment"
    }
  ]
}
```

## License

MIT — see [LICENSE](../LICENSE). CMS model specifications and coefficient data are U.S. government works in the public domain.
