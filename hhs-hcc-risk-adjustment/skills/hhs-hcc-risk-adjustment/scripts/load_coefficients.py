"""Load HHS-HCC model coefficients from CMS-published CSVs (stdlib only).

Usage:
    from load_coefficients import load_factors
    factors = load_factors('Adult', year=2025)
    factors['HHS_HCC042']['Silver_Level']  # -> 10.903

Returned dict structure:
    { variable_name: { 'Platinum_Level': float, 'Gold_Level': float, ... } }

Coefficient CSVs for BY2018–BY2027 are bundled in data/BY<YYYY>/ relative to
the repo root. Pass data_dir to override with a custom path.
"""

import csv
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
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {CSV_TO_INTERNAL.get(k, k): v for k, v in row.items()}
            var = normalized["Variable"]
            out[var] = {
                "Platinum_Level": float(normalized["Platinum_Level"]),
                "Gold_Level": float(normalized["Gold_Level"]),
                "Silver_Level": float(normalized["Silver_Level"]),
                "Bronze_Level": float(normalized["Bronze_Level"]),
                "Catastrophic_Level": float(normalized["Catastrophic_Level"]),
            }
    return out


def metal_column(metal: str) -> str:
    if metal not in METAL_COLS:
        raise ValueError(f"metal must be one of {list(METAL_COLS)}, got {metal!r}")
    return METAL_COLS[metal]
