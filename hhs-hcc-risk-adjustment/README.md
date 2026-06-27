# HHS-HCC Risk Adjustment — Claude Code Plugin

A [Claude Code](https://claude.ai/code) plugin that gives Claude deep expertise in the **HHS-HCC commercial risk adjustment model** — the CMS model used to calculate risk scores and transfer payments for ACA Individual and Small Group plans. Covers the current V07 model (BY2021–BY2027) and the earlier V05 model (BY2018–BY2020), with bundled coefficient data for all ten benefit years.

---

## What you can ask Claude

Once the plugin is installed, you can ask Claude questions like:

- *"What is the BY2025 Silver coefficient for HHS_HCC042?"*
- *"Score a 45-year-old female on a Silver CSR-1 plan with HCC042 and HCC156 flagged."*
- *"What changed in the severity model between BY2022 and BY2023?"*
- *"Why isn't this diabetes diagnosis contributing to the risk score?"*
- *"If our plan has a PLRS of 1.8 and statewide PLRS is 1.5, what's our transfer?"*
- *"Walk me through how the infant maturity × severity grid works."*
- *"Which ICD-10 codes map to HCC018?"*
- *"What J-codes trigger RXC_09?"*

Claude answers using the bundled reference data and scripts, citing the correct CMS rules for the benefit year you specify.

---

## Model coverage

| Sub-model | Who it covers | Key distinction |
|---|---|---|
| **Adult** | AGE_LAST ≥ 21 | HCC-additive; RXC interactions; severity/transplant counters; HCC_ED short-enrollment flag |
| **Child** | AGE_LAST 2–20 | HCC-additive; same group flags as Adult; different severity bucket schema (6_7 and 8PLUS) |
| **Infant** | AGE_LAST 0–1 | Maturity × severity interaction grid — does **not** score HCCs additively |

The model family depends on the benefit year: **V07** covers BY2021 and forward; **V05** covered BY2018–BY2020. Always confirm the benefit year before interpreting a coefficient — values change annually with the NBPP.

---

## Slash commands

| Command | What it does |
|---|---|
| `/hhs-hcc-score` | Guided intake → runs `score_enrollee.py` → explains the output clinically |
| `/hhs-hcc-lookup` | Look up any coefficient by variable name, year, and metal level |
| `/hhs-hcc-transfer` | Compute T(i) or find the Platinum inflection point; auto-populates statewide inputs by state+year |

Or just ask Claude a question directly — the plugin activates automatically based on context.

---

## Scripts

Pure Python 3.10+, stdlib only — no dependencies to install. Scripts live in `skills/hhs-hcc-risk-adjustment/scripts/`.

### Score an enrollee

```bash
python3 skills/hhs-hcc-risk-adjustment/scripts/score_enrollee.py \
  --age 45 --sex F --metal S --csr 1 --year 2025 \
  --hcc HHS_HCC042 HHS_HCC156 --rxc RXC_09 --enrol-duration 12
```

```
Sub-model: Adult
Metal: S (column Silver_Level)
BY: 2025

Variable                                  ind       coef    contrib
----------------------------------------------------------------------
HHS_HCC042                                  1    10.9030    10.9030
HHS_HCC156                                  1     7.4610     7.4610
RXC_09                                      1     0.6330     0.6330
FAGE_LAST_45_49                             1     0.2770     0.2770
----------------------------------------------------------------------
RAW SCORE                                                   19.2740
CSR factor (CSR_INDICATOR=1): 1.0000
CSR-ADJUSTED SCORE: 19.2740
```

**Key inputs:**

| Flag | Description |
|---|---|
| `--age` | `AGE_LAST` — age on the last day of the benefit year |
| `--sex` | `M` or `F` |
| `--metal` | `P` / `G` / `S` / `B` / `C` (or full name) |
| `--csr` | `RA_CSR_Indicator` — CMS internal CSR code (1 = standard/no CSR; 3 = Silver state-subsidy; 4 = ZCS Platinum; etc.) |
| `--year` | Benefit year — selects the bundled coefficient set |
| `--hcc` | Space-separated HCCs **after** hierarchy and group collapsing |
| `--rxc` | Space-separated RXCs (Adult model only) |
| `--enrol-duration` | Months enrolled (1–12) — triggers `HCC_ED` short-enrollment flag |
| `--data-dir` | Override the bundled data with a custom coefficient directory |

### Look up a coefficient

```bash
# Single metal
python3 skills/hhs-hcc-risk-adjustment/scripts/lookup.py \
  --year 2025 --model Adult --variable HHS_HCC042 --metal Silver
# → 10.9030

# All metals
python3 skills/hhs-hcc-risk-adjustment/scripts/lookup.py \
  --year 2025 --model Infant --variable EXTREMELY_IMMATURE_X_SEVERITY5
```

### Compute a risk transfer

```bash
# Transfer payment per billable member-month
python3 skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py \
  --plrs 1.8 --idf 1.08 --gcf 1.09 --av 0.8 --arf 1.90 \
  --statewide-plrs 1.5 --statewide-idf 1.03 --statewide-gcf 1.0 \
  --statewide-av 0.686 --statewide-arf 1.541 --premium 375

# Inflection point: at what PLRS does Platinum beat Gold?
python3 skills/hhs-hcc-risk-adjustment/scripts/risk_transfer.py --inflection \
  --arf 1.541 --statewide-plrs 1.5 --statewide-av 0.686 --statewide-arf 1.541
```

---

## Bundled data

All data lives under `skills/hhs-hcc-risk-adjustment/`.

### Coefficient CSVs — `data/BY<YYYY>/`

Three files per benefit year: `adult_model_factors.csv`, `child_model_factors.csv`, `infant_model_factors.csv`. Each row is a model variable with five metal-level coefficients (Platinum through Catastrophic).

| Folder | CMS source revision | Model family |
|--------|---------------------|--------------|
| BY2018 | `2018_DIY_120418` | V05 |
| BY2019 | `2019_DIY_041520` | V05 |
| BY2020 | `2020_DIY_080320` | V05 |
| BY2021 | `2021_DIY_033122` | V07 |
| BY2022 | `2022_DIY_122022` | V07 |
| BY2023 | `2023_NBPP_050622` | V07 |
| BY2024 | `2024_DIY_090624` | V07 |
| BY2025 | `2025_DIY_072325` | V07 |
| BY2026 | `2026_NBPP_100524` | V07 |
| BY2027 | `2027_NBPP_020926` | V07 |

Where CMS published both an initial NBPP release and a later DIY revision, the DIY revision is used — it supersedes the NBPP release and incorporates corrections.

### Cross-reference tables — `data/`

| File | Contents | Rows |
|------|----------|------|
| `hcc_labels.csv` | Human-readable label and clinical category for every HCC, group flag, RXC, and interaction variable | 210 |
| `csr_adjustment_factors.csv` | CSR adjustment factors by CSR_Code and model year (BY2020–BY2027) | 96 |
| `statewide_ra_factors.csv` | Statewide PLRS, IDF, AV, ARF, avg premium, and member months by state, market, and year (BY2018–BY2024) | 1,009 |

### Code-mapping tables — `references/`

| File | Contents | Rows |
|------|----------|------|
| `dx-mapping.csv` | Full ICD-10 → CC crosswalk with age/sex edits and effective date gating | 11,568 |
| `hcpcs-rxc.csv` | HCPCS J-code → RXC mapping | 86 |
| `ndc-rxc.csv` | NDC → RXC pharmacy mapping with start/end year | 15,134 |
| `service-code-reference.csv` | CPT/HCPCS qualifying-service-code list | 21,109 |

### Reference documents — `references/`

| File | Covers |
|------|--------|
| `model-overview.md` | V07 architecture, sub-models, scoring formula, key terminology |
| `adult-model.md` | Adult variables, group flags, severity/transplant buckets, HCC_ED, RXC interactions |
| `child-model.md` | Child variables, group flags, severity/transplant buckets (note 6_7 and 8PLUS collapsing) |
| `infant-model.md` | Maturity hierarchy, severity hierarchy, AGE0/AGE1 swap, maturity × severity grid |
| `cc-hcc-hierarchies.md` | DX → CC mapping, CC → HCC hierarchies, group collapsing, age/sex/MCE edits |
| `claim-qualification.md` | Which medical claims qualify for HCC scoring; why labs, DME, and J-code-only claims don't count |
| `rxc-interactions.md` | RXC variables, RXC_06 → RXC_07 hierarchy, HCC × RXC interactions including the RXC_09 triple |
| `csr-adjustments.md` | CSR adjustment factors by HIOS variant, RA_CSR_Indicator mapping, BY2025 schedule change |
| `risk-transfer-formula.md` | Full CMS risk transfer formula and metal-level optimization |
| `year-changes.md` | NBPP year-over-year model changes (BY2018–BY2027) |

---

## Background: what is HHS-HCC risk adjustment?

Under the ACA, CMS runs a risk adjustment program across all non-grandfathered Individual and Small Group plans. Plans with sicker-than-average enrollees receive transfer payments from plans with healthier-than-average enrollees. This levels the playing field and reduces incentives to cherry-pick healthy members.

The **HHS-HCC model** is the risk-scoring engine. It converts each enrollee's demographics, diagnoses (mapped from medical claims to Hierarchical Condition Categories), and pharmacy fills (mapped to RXC variables) into a **Plan Liability Risk Score (PLRS)**. The PLRS feeds into the CMS transfer formula alongside state-level Induced Demand Factors (IDF), Geographic Calibration Factors (GCF), actuarial values (AV), and allowable rating factors (ARF).

CMS publishes updated model specifications annually in the **Notice of Benefit and Payment Parameters (NBPP)** and releases SAS source code, DIY Excel workbooks, and (starting BY2025) a Python package. The SAS source is the authoritative spec when sources disagree.

---

## Installing the plugin

### Option 1 — npx (recommended)

```bash
npx hhs-hcc-risk-adjustment
```

This copies the plugin to `~/.claude/plugins/hhs-hcc-risk-adjustment/` and adds it to your global `~/.claude/settings.json` automatically. Restart Claude Code afterward.

Safe to re-run — it won't add a duplicate entry.

### Option 2 — manual

Clone the repo and add the plugin path to your Claude Code settings.

**User-level** (`~/.claude/settings.json`):
```json
{
  "plugins": [
    { "path": "/path/to/skills/hhs-hcc-risk-adjustment" }
  ]
}
```

**Project-level** (`.claude/settings.json` in your project):
```json
{
  "plugins": [
    { "path": "/path/to/skills/hhs-hcc-risk-adjustment" }
  ]
}
```

---

## License

Code and scripts: [MIT](../LICENSE) — © 2026 Wesley Sanders.

CMS model specifications, coefficient tables, and code-mapping crosswalks are U.S. government works in the public domain (published by the Centers for Medicare & Medicaid Services under the ACA risk adjustment program).
