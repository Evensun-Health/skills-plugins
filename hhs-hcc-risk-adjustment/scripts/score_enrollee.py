"""End-to-end risk score for one enrollee given demographics + flagged HCCs/RXCs.

Inputs are post-hierarchy/post-grouping HCC and RXC flags. Severity, transplant,
HCC_ED, RXC×HCC interactions, and the AGE0/AGE1 swap are derived automatically
based on the canonical CMS rules.

Usage:
    python3 score_enrollee.py --age 45 --sex F --metal S --csr 1 --year 2025 \\
        --hcc HHS_HCC042 HHS_HCC156 --rxc RXC_09 --enrol-duration 12
"""

import argparse
import sys
from pathlib import Path

from load_coefficients import FILE_BY_MODEL, load_factors, metal_column

# CSR adjustment factors by RA_CSR_Indicator (CMS internal numbering) and benefit year.
# BY2025 changed ZCS and LCS factors; BY2018–BY2024 shared the same schedule.
# See references/csr-adjustments.md for the full HIOS-suffix → indicator mapping.
_CSR_FACTORS: dict[int, dict[int, float]] = {
    # BY2018–BY2024: pre-schedule-change factors
    **{y: {1: 1.00, 2: 1.07, 3: 1.12, 4: 1.00, 5: 1.07, 6: 1.12, 7: 1.04,
           8: 1.07, 9: 1.10, 10: 1.12, 11: 1.15, 12: 1.00, 13: 1.07}
       for y in range(2018, 2025)},
    # BY2025+: updated ZCS (4,6,8,10) and LCS (5,7,9,11) schedule
    **{y: {1: 1.00, 2: 1.07, 3: 1.12, 4: 1.51, 5: 1.19, 6: 1.31, 7: 1.04,
           8: 1.39, 9: 1.10, 10: 1.46, 11: 1.15, 12: 1.51, 13: 1.07}
       for y in range(2025, 2028)},
}


def load_csr_factors(year: int) -> dict[int, float]:
    factors = _CSR_FACTORS.get(year)
    if factors is None:
        raise ValueError(f"No CSR factor schedule for year {year}. Supported: {sorted(_CSR_FACTORS)}")
    return factors

# === Sub-model selection ===
def pick_submodel(age_last: int) -> str:
    if age_last >= 21:
        return "Adult"
    if age_last >= 2:
        return "Child"
    return "Infant"


# === Adult/Child severe and transplant lists (PY2025) ===
ADULT_SEVERE_HCCS = {
    "HHS_HCC002", "HHS_HCC003", "HHS_HCC004", "HHS_HCC006", "HHS_HCC023",
    "HHS_HCC034", "HHS_HCC041", "HHS_HCC042", "HHS_HCC096", "HHS_HCC121",
    "HHS_HCC122", "HHS_HCC125", "HHS_HCC135", "HHS_HCC145", "HHS_HCC156",
    "HHS_HCC158", "HHS_HCC163", "HHS_HCC218", "HHS_HCC223", "HHS_HCC251",
    "G13", "G14", "G24",
}
CHILD_SEVERE_HCCS = (ADULT_SEVERE_HCCS - {"G24"}) | {"HHS_HCC018", "HHS_HCC183"}

ADULT_TRANSPLANT_HCCS = {"HHS_HCC034", "HHS_HCC041", "HHS_HCC158", "HHS_HCC251", "G14", "G24"}
CHILD_TRANSPLANT_HCCS = (ADULT_TRANSPLANT_HCCS - {"G24"}) | {"HHS_HCC018", "HHS_HCC183"}

# === RXC×HCC interactions (Adult) ===
RXC_HCC_INTERACTIONS = [
    ("RXC_01_X_HCC001", "RXC_01", {"HHS_HCC001"}),
    ("RXC_02_X_HCC037_1_036_035_2_035_1_034", "RXC_02",
     {"HHS_HCC034", "HHS_HCC035_1", "HHS_HCC035_2", "HHS_HCC036", "HHS_HCC037_1"}),
    ("RXC_03_X_HCC142", "RXC_03", {"HHS_HCC142"}),
    ("RXC_04_X_HCC184_183_187_188", "RXC_04",
     {"HHS_HCC183", "HHS_HCC184", "HHS_HCC187", "HHS_HCC188"}),
    ("RXC_05_X_HCC048_041", "RXC_05", {"HHS_HCC041", "HHS_HCC048"}),
    ("RXC_06_X_HCC018_019_020_021", "RXC_06",
     {"HHS_HCC018", "HHS_HCC019", "HHS_HCC020", "HHS_HCC021"}),
    ("RXC_07_X_HCC018_019_020_021", "RXC_07",
     {"HHS_HCC018", "HHS_HCC019", "HHS_HCC020", "HHS_HCC021"}),
    ("RXC_08_X_HCC118", "RXC_08", {"HHS_HCC118"}),
    ("RXC_09_X_HCC056", "RXC_09", {"HHS_HCC056"}),
    ("RXC_09_X_HCC057", "RXC_09", {"HHS_HCC057"}),
    ("RXC_09_X_HCC048_041", "RXC_09", {"HHS_HCC041", "HHS_HCC048"}),
    ("RXC_10_X_HCC159_158", "RXC_10", {"HHS_HCC158", "HHS_HCC159"}),
]


def derive_age_sex_var(age: int, sex: str) -> str | None:
    sx = sex.upper()
    if sx not in ("M", "F"):
        raise ValueError(f"sex must be M or F, got {sex!r}")
    if age == 0 and sx == "M":
        return "AGE0_MALE"
    if age == 1 and sx == "M":
        return "AGE1_MALE"
    if age <= 1:
        return None  # infant females have no demographic add-on
    bins = [(2, 4), (5, 9), (10, 14), (15, 20), (21, 24), (25, 29), (30, 34),
            (35, 39), (40, 44), (45, 49), (50, 54), (55, 59), (60, None)]
    for lo, hi in bins:
        if age >= lo and (hi is None or age <= hi):
            suffix = "GT" if hi is None else hi
            return f"{sx}AGE_LAST_{lo}_{suffix}"
    return None


def score_adult_or_child(model: str, age: int, sex: str, hccs: set[str],
                         rxcs: set[str], enrol_duration: int | None,
                         factors) -> dict:
    flags: dict[str, int] = {h: 1 for h in hccs}
    if model == "Adult":
        flags.update({r: 1 for r in rxcs})
        # Apply RXC_06 -> RXC_07 hierarchy
        if flags.get("RXC_06") == 1:
            flags["RXC_07"] = 0

        # RXC × HCC interactions
        for var, rxc_required, hcc_set in RXC_HCC_INTERACTIONS:
            if flags.get(rxc_required) == 1 and (hcc_set & hccs):
                flags[var] = 1
        # RXC_09 triple interaction
        if (flags.get("RXC_09") == 1
            and ("HHS_HCC056" in hccs or "HHS_HCC057" in hccs)
            and ("HHS_HCC048" in hccs or "HHS_HCC041" in hccs)):
            flags["RXC_09_X_HCC056_057_AND_048_041"] = 1

    # Age/sex variable
    age_sex = derive_age_sex_var(age, sex)
    if age_sex:
        flags[age_sex] = 1

    # HCC count: HCCs (excl HHS_HCC022) + Group flags. Inputs are post-grouping.
    hcc_cnt = sum(1 for v in hccs if v != "HHS_HCC022")

    # Severity / transplant
    severe_hccs = ADULT_SEVERE_HCCS if model == "Adult" else CHILD_SEVERE_HCCS
    transplant_hccs = ADULT_TRANSPLANT_HCCS if model == "Adult" else CHILD_TRANSPLANT_HCCS
    has_severe = bool(severe_hccs & hccs)
    has_transplant = bool(transplant_hccs & hccs)

    if model == "Adult":
        if has_severe:
            bucket = min(hcc_cnt, 10)
            flags[f"SEVERE_HCC_COUNT{bucket if bucket < 10 else '10PLUS'}"] = 1
        if has_transplant:
            bucket = min(max(hcc_cnt, 4), 8)
            flags[f"TRANSPLANT_HCC_COUNT{bucket if bucket < 8 else '8PLUS'}"] = 1
        if hcc_cnt > 0 and enrol_duration and 1 <= enrol_duration <= 6:
            flags[f"HCC_ED{enrol_duration}"] = 1
    else:  # Child
        if has_severe:
            if hcc_cnt <= 5:
                flags[f"SEVERE_HCC_COUNT{hcc_cnt}"] = 1
            elif hcc_cnt <= 7:
                flags["SEVERE_HCC_COUNT6_7"] = 1
            else:
                flags["SEVERE_HCC_COUNT8PLUS"] = 1
        if has_transplant and hcc_cnt >= 4:
            flags["TRANSPLANT_HCC_COUNT4PLUS"] = 1

    return flags


# === Infant model ===
INFANT_MATURITY_HCCS = {
    "IHCC_EXTREMELY_IMMATURE": {"HHS_HCC242", "HHS_HCC243", "HHS_HCC244"},
    "IHCC_IMMATURE": {"HHS_HCC245", "HHS_HCC246"},
    "IHCC_PREMATURE_MULTIPLES": {"HHS_HCC247", "HHS_HCC248"},
    "IHCC_TERM": {"HHS_HCC249"},
}
INFANT_MATURITY_ORDER = [
    "IHCC_EXTREMELY_IMMATURE", "IHCC_IMMATURE",
    "IHCC_PREMATURE_MULTIPLES", "IHCC_TERM", "IHCC_AGE1",
]

# Severity HCCs by year. Default = BY2025; older years differ for HCC070/HCC071.
def infant_severity_for_year(year: int) -> dict[str, set[str]]:
    sev5 = {"HHS_HCC008", "HHS_HCC018", "HHS_HCC034", "HHS_HCC041", "HHS_HCC042",
            "HHS_HCC125", "HHS_HCC128", "HHS_HCC129", "HHS_HCC130", "HHS_HCC137",
            "HHS_HCC158", "HHS_HCC183", "HHS_HCC184", "HHS_HCC251"}
    sev4 = {"HHS_HCC002", "HHS_HCC009", "HHS_HCC026", "HHS_HCC030", "HHS_HCC035_1",
            "HHS_HCC035_2", "HHS_HCC064", "HHS_HCC067", "HHS_HCC068", "HHS_HCC073",
            "HHS_HCC106", "HHS_HCC107", "HHS_HCC111", "HHS_HCC112", "HHS_HCC115",
            "HHS_HCC122", "HHS_HCC126", "HHS_HCC127", "HHS_HCC131", "HHS_HCC135",
            "HHS_HCC138", "HHS_HCC145", "HHS_HCC146", "HHS_HCC154", "HHS_HCC156",
            "HHS_HCC163", "HHS_HCC187", "HHS_HCC253"}
    sev3 = {"HHS_HCC001", "HHS_HCC003", "HHS_HCC006", "HHS_HCC010", "HHS_HCC011",
            "HHS_HCC012", "HHS_HCC027", "HHS_HCC045", "HHS_HCC054", "HHS_HCC055",
            "HHS_HCC061", "HHS_HCC063", "HHS_HCC066", "HHS_HCC074", "HHS_HCC075",
            "HHS_HCC081", "HHS_HCC082", "HHS_HCC083", "HHS_HCC084", "HHS_HCC096",
            "HHS_HCC108", "HHS_HCC109", "HHS_HCC110", "HHS_HCC113", "HHS_HCC114",
            "HHS_HCC117", "HHS_HCC119", "HHS_HCC121", "HHS_HCC132", "HHS_HCC139",
            "HHS_HCC142", "HHS_HCC149", "HHS_HCC150", "HHS_HCC159", "HHS_HCC218",
            "HHS_HCC223", "HHS_HCC226", "HHS_HCC228"}
    sev2 = {"HHS_HCC004", "HHS_HCC013", "HHS_HCC019", "HHS_HCC020", "HHS_HCC021",
            "HHS_HCC023", "HHS_HCC028", "HHS_HCC029", "HHS_HCC036", "HHS_HCC046",
            "HHS_HCC047", "HHS_HCC048", "HHS_HCC056", "HHS_HCC057", "HHS_HCC062",
            "HHS_HCC069", "HHS_HCC097", "HHS_HCC120", "HHS_HCC151", "HHS_HCC153",
            "HHS_HCC160", "HHS_HCC161_1", "HHS_HCC162", "HHS_HCC188", "HHS_HCC217",
            "HHS_HCC219"}
    sev1 = {"HHS_HCC037_1", "HHS_HCC037_2", "HHS_HCC102", "HHS_HCC103",
            "HHS_HCC118", "HHS_HCC161_2", "HHS_HCC234", "HHS_HCC254"}
    if year >= 2025:
        sev3 = sev3 | {"HHS_HCC070"}
        sev2 = sev2 | {"HHS_HCC071"}
    else:
        sev2 = sev2 | {"HHS_HCC070"}
        sev1 = sev1 | {"HHS_HCC071"}
    return {"IHCC_SEVERITY5": sev5, "IHCC_SEVERITY4": sev4, "IHCC_SEVERITY3": sev3,
            "IHCC_SEVERITY2": sev2, "IHCC_SEVERITY1": sev1}


def score_infant(age: int, sex: str, hccs: set[str], year: int) -> dict:
    flags: dict[str, int] = {}

    # Demographic add-on
    if age == 0 and sex.upper() == "M":
        flags["AGE0_MALE"] = 1
    elif age == 1 and sex.upper() == "M":
        flags["AGE1_MALE"] = 1

    # Maturity (highest wins). Only AGE_LAST=0 enrollees pick a non-AGE1 maturity.
    maturity = None
    if age == 0:
        for m, set_ in INFANT_MATURITY_HCCS.items():
            if set_ & hccs:
                maturity = m
                break  # ordered dict; first hit wins via natural priority
    if maturity is None:
        # AGE_LAST=1 enrollees, or AGE_LAST=0 with no maturity HCCs
        maturity = "IHCC_AGE1"
    flags[maturity] = 1

    # AGE0_MALE -> AGE1_MALE swap when AGE_LAST=0 and IHCC_AGE1=1 and AGE0_MALE=1
    if age == 0 and maturity == "IHCC_AGE1" and flags.get("AGE0_MALE") == 1:
        flags["AGE0_MALE"] = 0
        flags["AGE1_MALE"] = 1

    # Severity (highest wins)
    sev_map = infant_severity_for_year(year)
    severity = "IHCC_SEVERITY1"  # default
    for sev in ("IHCC_SEVERITY5", "IHCC_SEVERITY4", "IHCC_SEVERITY3", "IHCC_SEVERITY2"):
        if sev_map[sev] & hccs:
            severity = sev
            break
    flags[severity] = 1

    # Maturity x Severity interaction
    label = maturity.replace("IHCC_", "")
    sev_n = severity.replace("IHCC_SEVERITY", "")
    flags[f"{label}_X_SEVERITY{sev_n}"] = 1

    return flags


def score(model: str, flags: dict[str, int], factors: dict, metal: str) -> tuple[float, list[tuple[str, int, float, float]]]:
    col = metal_column(metal)
    contributions = []
    total = 0.0
    for var, ind in flags.items():
        if ind != 1:
            continue
        if var not in factors:
            continue  # ignore variables not in this model's factor table
        coef = float(factors[var][col])
        contrib = ind * coef
        total += contrib
        contributions.append((var, ind, coef, contrib))
    return total, contributions


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--age", required=True, type=int, help="AGE_LAST")
    p.add_argument("--sex", required=True, choices=["M", "F", "m", "f"])
    p.add_argument("--metal", required=True,
                   choices=["P", "G", "S", "B", "C", "Platinum", "Gold", "Silver", "Bronze", "Catastrophic"])
    p.add_argument("--csr", required=True, type=int, help="CSR_INDICATOR (numeric SQL code)")
    p.add_argument("--year", required=True, type=int)
    p.add_argument("--hcc", nargs="*", default=[], help="Flagged HCCs after hierarchy/grouping")
    p.add_argument("--rxc", nargs="*", default=[], help="Flagged RXCs (Adult only)")
    p.add_argument("--enrol-duration", type=int, default=None,
                   help="Months enrolled, integer 1-12 (only HCC_ED1-6 fire if HCC count > 0)")
    p.add_argument("--data-dir", default=None,
                   help="Custom path to coefficient CSVs; defaults to bundled data/BY<YEAR>/")
    args = p.parse_args()

    model = pick_submodel(args.age)
    factors = load_factors(model, data_dir=args.data_dir, year=args.year)

    hccs = set(args.hcc)
    rxcs = set(args.rxc)
    if model == "Infant":
        flags = score_infant(args.age, args.sex, hccs, args.year)
    else:
        flags = score_adult_or_child(model, args.age, args.sex, hccs, rxcs,
                                     args.enrol_duration, factors)

    raw, contribs = score(model, flags, factors, args.metal)
    csr_schedule = load_csr_factors(args.year)
    csr_factor = csr_schedule.get(args.csr, 1.0)
    csr_adjusted = raw * csr_factor

    print(f"Sub-model: {model}")
    print(f"Metal: {args.metal} (column {metal_column(args.metal)})")
    print(f"BY: {args.year}")
    print()
    print(f"{'Variable':40s} {'ind':>4s} {'coef':>10s} {'contrib':>10s}")
    print("-" * 70)
    for var, ind, coef, contrib in sorted(contribs, key=lambda x: -abs(x[3])):
        print(f"{var:40s} {ind:>4d} {coef:>10.4f} {contrib:>10.4f}")
    print("-" * 70)
    print(f"{'RAW SCORE':40s} {'':>4s} {'':>10s} {raw:>10.4f}")
    print(f"CSR factor (CSR_INDICATOR={args.csr}): {csr_factor:.4f}")
    print(f"CSR-ADJUSTED SCORE: {csr_adjusted:.4f}")


if __name__ == "__main__":
    main()
