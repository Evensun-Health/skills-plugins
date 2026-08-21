"""Load HHS-HCC model coefficients from CMS-published CSVs (stdlib only).

Usage:
    from load_coefficients import load_factors
    factors = load_factors('Adult', year=2025)
    factors['HHS_HCC042']['Silver_Level']  # -> 10.903

Returned dict structure:
    { variable_name: { 'Platinum_Level': float, 'Gold_Level': float, ... } }

Coefficient CSVs for BY2018–BY2027 are bundled in data/BY<YYYY>/ relative to
the repo root. Pass data_dir to override with a custom path.

Two naming conventions appear in CMS-published coefficient tables for the same
variables. The CMS software package uses `SEVERE_HCC_COUNT4` / `HCC_ED3` /
`ACF_PrEP`; the DIY reference workbooks use `SEVERE_4_HCC` / `ED_3` / `ACF_01`.
The DIY tables also expand collapsed tiers into one row per count (child
`SEVERE_6_HCC` and `SEVERE_7_HCC` both carry the `SEVERE_HCC_COUNT6_7` value).
Use `resolve()` rather than raw dict access so callers work against either
convention; it returns the matched variable name so the caller can report the
name actually used.
"""

import csv
import re
from pathlib import Path

# Repo root is two levels up from this script (scripts/ -> hhs-hcc-risk-adjustment/ -> /)
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = None  # resolved dynamically by year; see load_factors()

FILE_BY_MODEL = {
    "Adult": "adult_model_factors.csv",
    "Child": "child_model_factors.csv",
    "Infant": "infant_model_factors.csv",
}

METAL_COLS = {
    "P": "Platinum_Level",
    "G": "Gold_Level",
    "S": "Silver_Level",
    "B": "Bronze_Level",
    "C": "Catastrophic_Level",
    "Platinum": "Platinum_Level",
    "Gold": "Gold_Level",
    "Silver": "Silver_Level",
    "Bronze": "Bronze_Level",
    "Catastrophic": "Catastrophic_Level",
}

CSV_TO_INTERNAL = {
    "Variable": "Variable",
    "Platinum Level": "Platinum_Level",
    "Gold Level": "Gold_Level",
    "Silver Level": "Silver_Level",
    "Bronze Level": "Bronze_Level",
    "Catastrophic Level": "Catastrophic_Level",
}


def load_factors(model: str, data_dir=None, year: int | None = None) -> dict[str, dict[str, float]]:
    if model not in FILE_BY_MODEL:
        raise ValueError(f"model must be one of {list(FILE_BY_MODEL)}, got {model!r}")
    if data_dir is not None:
        base = Path(data_dir)
    elif year is not None:
        base = _REPO_ROOT / "data" / f"BY{year}"
        if not base.is_dir():
            raise ValueError(
                f"No bundled coefficients for BY{year}. "
                f"Expected directory: {base}. Pass --data-dir to use a custom path."
            )
    else:
        raise ValueError(
            "Specify either year= (to use bundled data/BY<YYYY>/ coefficients) "
            "or data_dir= (to use a custom path)."
        )
    path = base / FILE_BY_MODEL[model]
    out: dict[str, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {CSV_TO_INTERNAL.get(k, k): v for k, v in row.items()}
            var = normalized["Variable"].strip()
            out[var] = {
                "Platinum_Level": float(normalized["Platinum_Level"]),
                "Gold_Level": float(normalized["Gold_Level"]),
                "Silver_Level": float(normalized["Silver_Level"]),
                "Bronze_Level": float(normalized["Bronze_Level"]),
                "Catastrophic_Level": float(normalized["Catastrophic_Level"]),
            }
    _check_complete(model, out, path)
    return out


# Every published Adult/Child table carries a full age/sex block, so a table
# missing one is a truncated extract rather than a real model change. Scoring
# against it would quietly omit the demographic term.
_REQUIRED_AGE_SEX = {
    "Adult": [f"{sex}AGE_LAST_{band}" for sex in "MF" for band in
              ("21_24", "25_29", "30_34", "35_39", "40_44",
               "45_49", "50_54", "55_59", "60_GT")],
    "Child": [f"{sex}AGE_LAST_{band}" for sex in "MF" for band in
              ("2_4", "5_9", "10_14", "15_20")],
    "Infant": ["AGE0_MALE", "AGE1_MALE"],
}


def _check_complete(model: str, factors: dict, path) -> None:
    missing = [v for v in _REQUIRED_AGE_SEX[model] if v not in factors]
    if missing:
        raise ValueError(
            f"{path} is missing {len(missing)} of "
            f"{len(_REQUIRED_AGE_SEX[model])} {model} age/sex variables "
            f"(e.g. {', '.join(missing[:3])}). This coefficient table is an "
            f"incomplete extract and would produce scores that silently omit "
            f"the demographic term. Re-source it from the CMS software package "
            f"or DIY tables for that benefit year before scoring."
        )


def metal_column(metal: str) -> str:
    if metal not in METAL_COLS:
        raise ValueError(f"metal must be one of {list(METAL_COLS)}, got {metal!r}")
    return METAL_COLS[metal]


def resolve(factors: dict, variable: str) -> str | None:
    """Return the name under which `variable` exists in `factors`, or None.

    Tries the name as given, then the equivalent spelling in the other CMS
    naming convention, then (for the bucketed counters) the collapsed tier that
    covers the requested count.
    """
    for candidate in _candidates(variable):
        if candidate in factors:
            return candidate
    # Last resort: case-insensitive match, which covers the RXC interaction
    # rows that CMS spells `_X_` in some years and `_x_` in others.
    folded = {k.upper(): k for k in factors}
    for candidate in _candidates(variable):
        hit = folded.get(candidate.upper())
        if hit is not None:
            return hit
    return None


def _candidates(variable: str):
    """Yield every spelling of `variable` that a CMS coefficient table may use."""
    yield variable

    m = re.fullmatch(r"SEVERE_HCC_COUNT(\d+)", variable)
    if m:
        n = int(m.group(1))
        yield f"SEVERE_{n}_HCC"
        # Collapsed tiers, widest-count first so a count of 10 prefers 10PLUS.
        if n >= 10:
            yield "SEVERE_HCC_COUNT10PLUS"
            yield "SEVERE_10_HCC"
        if n >= 8:
            yield "SEVERE_HCC_COUNT8PLUS"
            yield "SEVERE_8_HCC"
        if n in (6, 7):
            yield "SEVERE_HCC_COUNT6_7"
            yield "SEVERE_6_HCC"

    m = re.fullmatch(r"TRANSPLANT_HCC_COUNT(\d+)", variable)
    if m:
        n = int(m.group(1))
        yield f"TRANSPLANT_{n}_HCC"
        if n >= 8:
            yield "TRANSPLANT_HCC_COUNT8PLUS"
            yield "TRANSPLANT_8_HCC"
        if n >= 4:
            yield "TRANSPLANT_HCC_COUNT4PLUS"
            yield "TRANSPLANT_4_HCC"

    m = re.fullmatch(r"HCC_ED(\d+)", variable)
    if m:
        yield f"ED_{m.group(1)}"

    # ACF (Additional Cost Factor), new in BY2026. The CMS package names the
    # adult and child rows separately; the DIY workbook calls both ACF_01.
    if variable in ("ACF_PrEP", "ACF_PrEP_Child"):
        yield "ACF_01"
