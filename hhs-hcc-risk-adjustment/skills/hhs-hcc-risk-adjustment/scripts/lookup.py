"""Quick coefficient lookup by (model, variable, metal).

Usage:
    python3 lookup.py --year 2025 --model Adult --variable HHS_HCC042 --metal Silver
    python3 lookup.py --year 2025 --model Infant --variable EXTREMELY_IMMATURE_X_SEVERITY5

--year selects the bundled data/BY<YEAR>/ table. Pass --data-dir to read a
custom directory instead. Variable names may use either CMS naming convention
(`SEVERE_HCC_COUNT4` or `SEVERE_4_HCC`); the lookup reports which name matched.
"""

import argparse
import sys

from load_coefficients import FILE_BY_MODEL, METAL_COLS, load_factors, metal_column, resolve


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", required=True, type=int, help="Benefit year (selects bundled data/BY<YEAR>/)")
    p.add_argument("--model", required=True, choices=list(FILE_BY_MODEL))
    p.add_argument("--variable", required=True)
    p.add_argument("--metal", default=None, choices=list(METAL_COLS) + [None],
                   help="If omitted, prints all five metals")
    p.add_argument("--data-dir", default=None,
                   help="Custom path to coefficient CSVs; defaults to bundled data/BY<YEAR>/")
    args = p.parse_args()

    factors = load_factors(args.model, data_dir=args.data_dir, year=args.year)
    matched = resolve(factors, args.variable)
    if matched is None:
        sample = list(factors.keys())[:5]
        print(f"ERROR: variable {args.variable!r} not found in {args.model} BY{args.year} "
              f"factors. Did you mean one of these (first few): {sample}...", file=sys.stderr)
        sys.exit(2)
    if matched != args.variable:
        print(f"note: {args.variable} resolved to {matched} in the BY{args.year} table",
              file=sys.stderr)

    row = factors[matched]
    if args.metal is None:
        print(f"{args.model} {matched} (BY{args.year}):")
        for label in ("Platinum_Level", "Gold_Level", "Silver_Level", "Bronze_Level", "Catastrophic_Level"):
            print(f"  {label.replace('_Level', ''):14s} {row[label]:.4f}")
    else:
        col = metal_column(args.metal)
        print(f"{row[col]:.4f}")


if __name__ == "__main__":
    main()
