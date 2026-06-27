"""Compute the CMS risk transfer T(i) and the metal-level inflection point.

T(i) per billable member-month:
    T(i) = [ PLRS_i * IDF_i * GCF_i / S_plrs
           - AV_i  * ARF_i * IDF_i * GCF_i / S_avarf ] * Pbar

where S_plrs and S_avarf are statewide weighted averages.

Inflection PLRS (gold->platinum, conservative; assumes constant PLRS across metals):
    PLRS_critical = 2.44286 * ARF_i * PLRS_s / (AV_s * ARF_s)

If PLRS_i > PLRS_critical -> Platinum is favorable for that ARF (purely from a
risk-transfer perspective, before considering premium).

Usage examples:
    python3 risk_transfer.py --plrs 1.8 --idf 1.08 --gcf 1.09 --av 0.8 --arf 1.90 \\
        --statewide-plrs 1.5 --statewide-idf 1.03 --statewide-gcf 1.0 \\
        --statewide-av 0.686 --statewide-arf 1.541 --premium 375

    python3 risk_transfer.py --inflection --arf 1.541 \\
        --statewide-plrs 1.5 --statewide-av 0.686 --statewide-arf 1.541
"""

import argparse


def compute_transfer(plrs_i, idf_i, gcf_i, av_i, arf_i,
                     plrs_s, idf_s, gcf_s, av_s, arf_s,
                     premium):
    """Returns (T_per_mm, left_side, right_side)."""
    # Statewide weighted averages — supplied directly. Treated as scalar denominators.
    s_plrs = plrs_s * idf_s * gcf_s
    s_avarf = av_s * arf_s * idf_s * gcf_s
    left = (plrs_i * idf_i * gcf_i) / s_plrs
    right = (av_i * arf_i * idf_i * gcf_i) / s_avarf
    transfer = (left - right) * premium
    return transfer, left, right


def inflection_plrs(arf_i, plrs_s, av_s, arf_s):
    """PLRS above which a Gold->Platinum shift is favorable (transfer-only)."""
    return 2.44286 * arf_i * plrs_s / (av_s * arf_s)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inflection", action="store_true",
                   help="Compute inflection PLRS instead of T(i)")

    # Plan-level
    p.add_argument("--plrs", type=float, help="Plan PLRS_i")
    p.add_argument("--idf", type=float, help="Plan IDF_i")
    p.add_argument("--gcf", type=float, help="Plan GCF_i")
    p.add_argument("--av", type=float, help="Plan AV_i")
    p.add_argument("--arf", type=float, help="Plan ARF_i")

    # Statewide
    p.add_argument("--statewide-plrs", type=float, required=True, dest="plrs_s",
                   help="Statewide weighted-average PLRS")
    p.add_argument("--statewide-idf", type=float, dest="idf_s",
                   help="Statewide weighted-average IDF (transfer mode only)")
    p.add_argument("--statewide-gcf", type=float, dest="gcf_s",
                   help="Statewide weighted-average GCF (transfer mode only)")
    p.add_argument("--statewide-av", type=float, required=True, dest="av_s",
                   help="Statewide weighted-average AV")
    p.add_argument("--statewide-arf", type=float, required=True, dest="arf_s",
                   help="Statewide weighted-average ARF")

    p.add_argument("--premium", type=float, help="Statewide average premium P-bar (transfer mode only)")
    args = p.parse_args()

    if args.inflection:
        if args.arf is None:
            p.error("--inflection requires --arf (the plan's ARF)")
        critical = inflection_plrs(args.arf, args.plrs_s, args.av_s, args.arf_s)
        print(f"Inflection PLRS for ARF={args.arf}: {critical:.4f}")
        print(f"  If projected PLRS > {critical:.4f}, Platinum is favorable for this ARF (transfer only)")
        print(f"  If projected PLRS < {critical:.4f}, Gold is favorable")
        return

    required = ["plrs", "idf", "gcf", "av", "arf", "idf_s", "gcf_s", "premium"]
    missing = [r for r in required if getattr(args, r) is None]
    if missing:
        p.error(f"Transfer computation requires --{', --'.join(m.replace('_', '-') for m in missing)}")

    transfer, left, right = compute_transfer(
        args.plrs, args.idf, args.gcf, args.av, args.arf,
        args.plrs_s, args.idf_s, args.gcf_s, args.av_s, args.arf_s,
        args.premium,
    )
    print(f"Left side  (PLRS·IDF·GCF / statewide):     {left:.6f}")
    print(f"Right side (AV·ARF·IDF·GCF / statewide):   {right:.6f}")
    print(f"Difference (left - right):                 {left - right:+.6f}")
    print(f"Statewide average premium (P-bar):         ${args.premium:.2f}")
    print()
    print(f"T(i) per billable member-month:            ${transfer:+.2f}")
    if transfer > 0:
        print("  Plan RECEIVES this amount.")
    elif transfer < 0:
        print("  Plan PAYS this amount in.")
    else:
        print("  Net-zero transfer.")


if __name__ == "__main__":
    main()
