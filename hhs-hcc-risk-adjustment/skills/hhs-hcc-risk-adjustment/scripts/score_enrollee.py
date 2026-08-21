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

from load_coefficients import FILE_BY_MODEL, load_factors, metal_column, resolve

# CSR adjustment factors by RA_CSR_Indicator (the CMS person-level indicator,
# 1-11) and benefit year. Verified against CSR_table.csv in the CMS BY2026
# software package. Indicator -> plan variation, per the CMS software writeup:
#   1  non-CSR / unknown / 73% AV Silver / state-subsidy Silver
#   2  state-subsidy Gold                3  87% and 94% AV Silver
#   4  Zero Cost Sharing Bronze          5  Limited Cost Sharing Bronze
#   6  Zero Cost Sharing Platinum        7  Limited Cost Sharing Platinum
#   8  Zero Cost Sharing Gold            9  Limited Cost Sharing Gold
#   10 Zero Cost Sharing Silver          11 Limited Cost Sharing Silver
# BY2025 raised the Zero and Limited Cost Sharing factors; BY2018-BY2024 shared
# the earlier schedule. See references/csr-adjustments.md.
#
# Only the BY2025+ row is verified against a CMS CSR_table.csv. The BY2018-BY2024
# row is reconstructed by applying that year's published per-metal factors to the
# indicator numbering above; confirm against the CSR_table.csv in the relevant
# year's CMS software package before relying on it for a pre-BY2025 restatement.
_CSR_FACTORS: dict[int, dict[int, float]] = {
    # BY2018–BY2024
    **{y: {1: 1.00, 2: 1.07, 3: 1.12, 4: 1.15, 5: 1.15, 6: 1.00, 7: 1.00,
           8: 1.07, 9: 1.07, 10: 1.12, 11: 1.12}
       for y in range(2018, 2025)},
    # BY2025+
    **{y: {1: 1.00, 2: 1.07, 3: 1.12, 4: 1.51, 5: 1.19, 6: 1.31, 7: 1.04,
           8: 1.39, 9: 1.10, 10: 1.46, 11: 1.15}
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


# === Pre-BY2023 severity model (Adult only) ===
# BY2018-BY2022 had no SEVERE_HCC_COUNT*/TRANSPLANT_HCC_COUNT* counters. Instead a
# single SEVERE_V3 flag was crossed with specific HCCs to produce one of two
# interaction groups. Verified against the CMS SAS model macros: V0518F3M.SAS,
# V0519F3M.SAS, V0520F5M.SAS, CY21M07C.SAS, CY22M07C.SAS.
SEVERE_V3_HCCS = {
    "HHS_HCC002", "HHS_HCC042", "HHS_HCC120", "HHS_HCC122",
    "HHS_HCC125", "HHS_HCC126", "HHS_HCC127", "HHS_HCC156",
}
# The group token was renamed G06 -> G06A in the BY2021 V07 relabeling.
_INT_GROUP_H_BASE = {"HHS_HCC006", "HHS_HCC008", "HHS_HCC009", "HHS_HCC010",
                     "HHS_HCC115", "HHS_HCC135", "HHS_HCC145", "G08"}
# INT_GROUP_M existed only in V05 (BY2018-BY2020); BY2021 dropped it entirely.
INT_GROUP_M_HCCS = {"HHS_HCC035", "HHS_HCC038", "HHS_HCC153",
                    "HHS_HCC154", "HHS_HCC163", "HHS_HCC253", "G03"}


def int_group_h_members(year: int) -> set[str]:
    return _INT_GROUP_H_BASE | ({"G06"} if year <= 2020 else {"G06A"})


# === Adult/Child severe and transplant lists (BY2023+) ===
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

# === Group flags (Adult/Child) ===
# Needed to expand a post-grouping input back to its member HCCs: CMS tests the
# RXC x HCC interaction lists against both pre- and post-grouping HCC values,
# and several interaction HCCs are group members (HCC018/183 -> G24,
# HCC019/020/021 -> G01, HCC187/188 -> G16).
ADULT_GROUPS = {
    "G01": {"HHS_HCC019", "HHS_HCC020", "HHS_HCC021"},
    "G02B": {"HHS_HCC026", "HHS_HCC027"},
    "G04": {"HHS_HCC061", "HHS_HCC062"},
    "G06A": {"HHS_HCC067", "HHS_HCC068", "HHS_HCC069"},
    "G08": {"HHS_HCC073", "HHS_HCC074"},
    "G09A": {"HHS_HCC081", "HHS_HCC082"},
    "G09C": {"HHS_HCC083", "HHS_HCC084"},
    "G10": {"HHS_HCC106", "HHS_HCC107"},
    "G11": {"HHS_HCC108", "HHS_HCC109"},
    "G12": {"HHS_HCC117", "HHS_HCC119"},
    "G13": {"HHS_HCC126", "HHS_HCC127"},
    "G14": {"HHS_HCC128", "HHS_HCC129"},
    "G21": {"HHS_HCC137", "HHS_HCC138", "HHS_HCC139"},
    "G15A": {"HHS_HCC160", "HHS_HCC161_1", "HHS_HCC161_2"},
    "G16": {"HHS_HCC187", "HHS_HCC188"},
    "G17A": {"HHS_HCC204", "HHS_HCC205"},
    "G18A": {"HHS_HCC207", "HHS_HCC208"},
    "G24": {"HHS_HCC018", "HHS_HCC183"},
}
CHILD_GROUPS = {
    "G01": {"HHS_HCC019", "HHS_HCC020", "HHS_HCC021"},
    "G02B": {"HHS_HCC026", "HHS_HCC027"},
    "G02D": {"HHS_HCC028", "HHS_HCC029"},
    "G03": {"HHS_HCC054", "HHS_HCC055"},
    "G04": {"HHS_HCC061", "HHS_HCC062"},
    "G06A": {"HHS_HCC067", "HHS_HCC068", "HHS_HCC069"},
    "G08": {"HHS_HCC073", "HHS_HCC074"},
    "G09A": {"HHS_HCC081", "HHS_HCC082"},
    "G09C": {"HHS_HCC083", "HHS_HCC084"},
    "G10": {"HHS_HCC106", "HHS_HCC107"},
    "G11": {"HHS_HCC108", "HHS_HCC109"},
    "G12": {"HHS_HCC117", "HHS_HCC119"},
    "G13": {"HHS_HCC126", "HHS_HCC127"},
    "G14": {"HHS_HCC128", "HHS_HCC129"},
    "G16": {"HHS_HCC187", "HHS_HCC188"},
    "G17A": {"HHS_HCC204", "HHS_HCC205"},
    "G18A": {"HHS_HCC207", "HHS_HCC208"},
    "G19B": {"HHS_HCC210", "HHS_HCC211"},
    "G22": {"HHS_HCC234", "HHS_HCC254"},
    "G23": {"HHS_HCC131", "HHS_HCC132"},
}
# G07A (HCC070, HCC071) applied through BY2024 and was removed in BY2025.
G07A_MEMBERS = {"HHS_HCC070", "HHS_HCC071"}


def expand_groups(model: str, hccs: set[str], year: int) -> set[str]:
    """Add back the member HCCs implied by any group flag in `hccs`.

    CMS evaluates the RXC x HCC interaction lists against pre-grouping HCCs as
    well as post-grouping ones. Callers pass post-grouping input, so a group
    flag has to stand in for the HCCs it absorbed.

    The group names here are the V07 set (BY2021+). V05 (BY2018-BY2020) used
    G02A/G03/G06/G07/G09/G15/G17/G18 where V07 uses G02B/G06A/G07A/G09A/G09C/
    G15A/G17A/G18A, and V05 HCC numbering is not the same either. The names that
    do carry over unchanged (G01, G04, G08, G10-G14, G16) cover every group whose
    members appear in a V05 severity list, so the difference does not affect
    pre-BY2021 scoring; RXC interactions, the other consumer, did not exist yet.
    """
    groups = dict(ADULT_GROUPS if model == "Adult" else CHILD_GROUPS)
    if year <= 2024:
        groups["G07A"] = G07A_MEMBERS
    if year < 2024:
        groups.pop("G24", None)   # G24 was introduced in BY2024
    expanded = set(hccs)
    for flag, members in groups.items():
        if flag in hccs:
            expanded |= members
    return expanded


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
                         year: int, acf: bool = False) -> dict:
    flags: dict[str, int] = {h: 1 for h in hccs}
    # Group flags stand in for the HCCs they absorbed when testing interaction
    # membership, matching CMS's pre-and-post-grouping check.
    hccs_expanded = expand_groups(model, hccs, year)

    if model == "Adult":
        flags.update({r: 1 for r in rxcs})
        # Apply RXC_06 -> RXC_07 hierarchy
        if flags.get("RXC_06") == 1:
            flags["RXC_07"] = 0

        # RXC × HCC interactions
        for var, rxc_required, hcc_set in RXC_HCC_INTERACTIONS:
            if flags.get(rxc_required) == 1 and (hcc_set & hccs_expanded):
                flags[var] = 1
        # RXC_09 triple interaction
        if (flags.get("RXC_09") == 1
            and ("HHS_HCC056" in hccs_expanded or "HHS_HCC057" in hccs_expanded)
            and ("HHS_HCC048" in hccs_expanded or "HHS_HCC041" in hccs_expanded)):
            flags["RXC_09_X_HCC056_057_AND_048_041"] = 1
        if acf:
            flags["ACF_PrEP"] = 1
    elif acf:
        flags["ACF_PrEP_Child"] = 1

    # Age/sex variable
    age_sex = derive_age_sex_var(age, sex)
    if age_sex:
        flags[age_sex] = 1

    # HCC count: HCCs (excl HHS_HCC022) + Group flags. Inputs are post-grouping.
    hcc_cnt = sum(1 for v in hccs if v != "HHS_HCC022")

    if year >= 2023:
        # Severity / transplant counters.
        severe_hccs = ADULT_SEVERE_HCCS if model == "Adult" else CHILD_SEVERE_HCCS
        transplant_hccs = ADULT_TRANSPLANT_HCCS if model == "Adult" else CHILD_TRANSPLANT_HCCS
        # Both counters key off the exact HCC count, and both start at a floor: the
        # adult transplant counters begin at 4 and the child counter at 4PLUS, so a
        # transplant enrollee with fewer than 4 counted HCCs gets no counter at all.
        if (severe_hccs & hccs) and hcc_cnt >= 1:
            flags[f"SEVERE_HCC_COUNT{min(hcc_cnt, 10)}"] = 1
        if (transplant_hccs & hccs) and hcc_cnt >= 4:
            flags[f"TRANSPLANT_HCC_COUNT{min(hcc_cnt, 8)}"] = 1
        # HCC-contingent enrollment duration, 6 buckets.
        if model == "Adult" and hcc_cnt > 0 and enrol_duration and 1 <= enrol_duration <= 6:
            flags[f"HCC_ED{enrol_duration}"] = 1
    else:
        # BY2018-BY2022: SEVERE_V3 crossed with specific HCCs. Adult only; the
        # child model of this era carries no severity variable.
        if model == "Adult" and (SEVERE_V3_HCCS & hccs_expanded):
            if int_group_h_members(year) & hccs_expanded:
                flags["INT_GROUP_H"] = 1
            elif year <= 2020 and (INT_GROUP_M_HCCS & hccs_expanded):
                # INT_GROUP_M is gated on INT_GROUP_H = 0 and existed only in V05.
                flags["INT_GROUP_M"] = 1
        # Enrollment duration: 11 buckets, and NOT contingent on HCC count.
        # ENROLDURATION = 12 is the omitted reference category.
        if model == "Adult" and enrol_duration and 1 <= enrol_duration <= 11:
            flags[f"ED_{enrol_duration}"] = 1

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


def score_infant(age: int, sex: str, hccs: set[str], year: int) -> tuple[dict, dict]:
    """Return (scoring flags, derived intermediates).

    Only AGE0_MALE/AGE1_MALE and the single maturity x severity interaction
    carry coefficients. The bare maturity and severity flags are intermediates
    that drive the interaction, so they are returned separately rather than
    handed to the scorer, which would report them as unmatched variables.
    """
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

    # Maturity x Severity interaction
    label = maturity.replace("IHCC_", "")
    sev_n = severity.replace("IHCC_SEVERITY", "")
    flags[f"{label}_X_SEVERITY{sev_n}"] = 1

    return flags, {maturity: 1, severity: 1}


def score(model: str, flags: dict[str, int], factors: dict,
          metal: str) -> tuple[float, list[tuple[str, int, float, float]], list[str]]:
    """Sum the coefficient for every set flag.

    Returns the total, the per-variable contributions, and the names of any set
    flags that had no coefficient row. An unmatched flag is reported rather than
    dropped silently: a missing severity or interaction row understates the
    score by several points and must not pass unnoticed.
    """
    col = metal_column(metal)
    contributions = []
    unmatched = []
    total = 0.0
    for var, ind in flags.items():
        if ind != 1:
            continue
        matched = resolve(factors, var)
        if matched is None:
            unmatched.append(var)
            continue
        coef = float(factors[matched][col])
        label = var if matched == var else f"{var} (as {matched})"
        total += coef
        contributions.append((label, ind, coef, coef))
    return total, contributions, unmatched


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
    p.add_argument("--acf", action="store_true",
                   help="Enrollee qualifies for the PrEP Additional Cost Factor (BY2026+)")
    p.add_argument("--data-dir", default=None,
                   help="Custom path to coefficient CSVs; defaults to bundled data/BY<YEAR>/")
    args = p.parse_args()

    model = pick_submodel(args.age)
    factors = load_factors(model, data_dir=args.data_dir, year=args.year)

    hccs = set(args.hcc)
    rxcs = set(args.rxc)
    derived: dict[str, int] = {}
    if model == "Infant":
        flags, derived = score_infant(args.age, args.sex, hccs, args.year)
    else:
        flags = score_adult_or_child(model, args.age, args.sex, hccs, rxcs,
                                     args.enrol_duration, args.year, acf=args.acf)

    raw, contribs, unmatched = score(model, flags, factors, args.metal)
    csr_schedule = load_csr_factors(args.year)
    if args.csr not in csr_schedule:
        raise SystemExit(
            f"ERROR: CSR_INDICATOR {args.csr} is not defined for BY{args.year}. "
            f"CMS defines {min(csr_schedule)}-{max(csr_schedule)}; "
            f"non-CSR enrollees are 1. See references/csr-adjustments.md."
        )
    csr_factor = csr_schedule[args.csr]
    csr_adjusted = raw * csr_factor

    print(f"Sub-model: {model}")
    print(f"Metal: {args.metal} (column {metal_column(args.metal)})")
    print(f"BY: {args.year}")
    if derived:
        print(f"Derived (not scored directly): {', '.join(sorted(derived))}")
    print()
    print(f"{'Variable':45s} {'ind':>4s} {'coef':>10s} {'contrib':>10s}")
    print("-" * 75)
    for var, ind, coef, contrib in sorted(contribs, key=lambda x: -abs(x[3])):
        print(f"{var:45s} {ind:>4d} {coef:>10.4f} {contrib:>10.4f}")
    print("-" * 75)
    print(f"{'RAW SCORE':45s} {'':>4s} {'':>10s} {raw:>10.4f}")
    print(f"CSR factor (CSR_INDICATOR={args.csr}): {csr_factor:.4f}")
    print(f"CSR-ADJUSTED SCORE: {csr_adjusted:.4f}")

    if unmatched:
        print(file=sys.stderr)
        print(f"WARNING: {len(unmatched)} set variable(s) had no coefficient row in the "
              f"{model} BY{args.year} factor table and contributed 0:", file=sys.stderr)
        for var in sorted(unmatched):
            print(f"  {var}", file=sys.stderr)
        print("The score above is therefore incomplete. Check the variable name against "
              "the factor table for this benefit year.", file=sys.stderr)


if __name__ == "__main__":
    main()
