#!/usr/bin/env python3
"""Align the skill's BY2026 reference data with an EDGE Global Reference Data workbook.

Source: the monthly "Global-Ref-Data-Update-*.xlsx" that CMS deploys to the EDGE
server (title rows 1-2, header row 4, data from row 5; OPERATION is OLD / NEW /
UPDATE / DELETE).  The workbook lists the *complete* table every time, so it can
be applied as a full snapshot.

What this script does (dry run unless --write):

  1. data/BY<year>/{adult,child,infant}_model_factors.csv
       Every EDGE factor is mapped to the CMS-package variable name and compared with
       the CSV; differing cells are rewritten in place.  Variables EDGE does not
       publish (ACF_PrEP, ACF_PrEP_Child) are left alone.
  2. references/ndc-rxc.csv
       EDGE DELETE rows still valid in <year> are end-dated at <year>-1 (history is kept);
       EDGE-active mappings that are not valid in <year> get a new <year>-<year+1> row.
       ACF_* rows are never touched (the workbook does not carry them).
  3. references/hcpcs-rxc.csv  (no year columns, so this one is a true add/remove)
       DELETE rows and non-ACF rows EDGE no longer lists are removed; missing ones added.

Usage:
    python tools/edge_ref_update.py WORKBOOK.xlsx [--skill-dir DIR] [--year 2026] [--write]

Needs pandas + openpyxl.  Existing line endings / BOM are preserved.
"""
import argparse
import io
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

METALS = ['01', '02', '03', '04', '05']  # Platinum, Gold, Silver, Bronze, Catastrophic
HCC_SUFFIX = {'351': '035_1', '352': '035_2', '371': '037_1', '372': '037_2',
              '871': '087_1', '872': '087_2', '1611': '161_1', '1612': '161_2'}
MATURITY = {'A1': 'AGE1', 'EI': 'EXTREMELY_IMMATURE', 'I': 'IMMATURE',
            'PM': 'PREMATURE_MULTIPLES', 'T': 'TERM'}
DEFAULT_SKILL = Path(__file__).resolve().parent.parent / 'hhs-hcc-risk-adjustment' / 'skills' / 'hhs-hcc-risk-adjustment'


def read_sheet(path, sheet):
    return pd.read_excel(path, sheet_name=sheet, header=3, dtype=str, engine='openpyxl')


def build_factors(path):
    """Return {'Adult'|'Child'|'Infant': {variable: [P, G, S, B, C]}} in CMS-package names."""
    out = {}

    def put(model, var, level, value):
        row = out.setdefault(model, {}).setdefault(var, [None] * 5)
        i = METALS.index(level)
        assert row[i] is None, (model, var, level, 'duplicate')
        row[i] = float(value)

    for r in read_sheet(path, 'Demographic Factors').itertuples():
        lo, hi = int(r.AGE_MIN_INCL), int(r.AGE_MAX_EXCL)
        if r.AGE_MDL_TYP == 'Infant':
            var = f'AGE{lo}_MALE'
        else:
            band = f'{lo}_GT' if hi >= 999 else f'{lo}_{hi - 1}'
            var = f'{r.GENDER_TYPE}AGE_LAST_{band}'
        put(r.AGE_MDL_TYP, var, r.MTL_LVL_CD, r.DMGRPHC_FCTR)

    # An HCC inside a group carries 0 on its own row; the value sits on the G-group row.
    for r in read_sheet(path, 'HCC and HCC Group Factors').itertuples():
        if r.HCC_CD != 'BLNK':
            assert r.GRP_CD == 'BLNK'
            var = f'HHS_HCC{HCC_SUFFIX.get(r.HCC_CD, r.HCC_CD.zfill(3))}'
        else:
            var = r.GRP_CD
        put(r.AGE_MDL_TYP, var, r.MTL_LVL_CD, r.FACTOR_QTY)

    # Severity / transplant counters.  The CMS package collapses tiers into one column:
    # Adult SEVERE 10+, TRANSPLANT 8+; Child SEVERE 6-7 share a column, 8+ and
    # TRANSPLANT 4+.  Every count in a collapsed tier must carry the same value.
    for r in read_sheet(path, 'HCCCOUNT_SEVTRANSPLANT_FACTOR').itertuples():
        n = int(r.HCC_COUNT)
        if r.SEVERITY_TYPE == 'S':
            if r.AGE_MODEL == 'Adult':
                tag = '10PLUS' if n >= 10 else str(n)
            else:
                tag = '6_7' if n in (6, 7) else '8PLUS' if n >= 8 else str(n)
            var = f'SEVERE_HCC_COUNT{tag}'
        else:
            tag = ('8PLUS' if n >= 8 else str(n)) if r.AGE_MODEL == 'Adult' else '4PLUS'
            var = f'TRANSPLANT_HCC_COUNT{tag}'
        row = out.setdefault(r.AGE_MODEL, {}).setdefault(var, [None] * 5)
        i = METALS.index(r.MTL_LVL_CD)
        if row[i] is not None:
            assert abs(row[i] - float(r.FACTOR_QTY)) < 1e-9, (r.AGE_MODEL, var, n, row[i], r.FACTOR_QTY)
        row[i] = float(r.FACTOR_QTY)

    # Enrollment-duration factors: Adult only; months 7-12 are zero and not stored.
    for r in read_sheet(path, 'HCC_ENROLLMENT_DURATION_FACTOR').itertuples():
        m = int(r.ENROLLMENT_MONTHS)
        if m <= 6:
            assert r.HCC_COUNT == '1'
            put('Adult', f'HCC_ED{m}', r.MTL_LVL_CD, r.FACTOR_QTY)
        else:
            assert float(r.FACTOR_QTY) == 0

    for r in read_sheet(path, 'Infant Severity Maturity Factor').itertuples():
        put('Infant', f'{MATURITY[r.MATURITY_CD]}_X_SEVERITY{r.SVRTY_TYP_CD[1]}',
            r.MTL_LVL_CD, r.INFNT_SVRTY_MTRTY_FCTR)

    for r in read_sheet(path, 'RXC_STANDALONE_FACTOR').itertuples():
        assert r.MODEL_TYPE == 'ADULT'
        put('Adult', f'RXC_{int(r.RXC):02d}', r.MTL_LVL, r.FACTOR)
    for r in read_sheet(path, 'RXC_HCC_INTERACTION_FACTOR').itertuples():
        assert r.MODEL_TYPE == 'ADULT'
        put('Adult', r.INTERACTION, r.MTL_LVL, r.FACTOR)

    for model in out.values():
        for var, vals in model.items():
            assert None not in vals, var
    return out


def fmt(v):
    return str(int(v)) if v == int(v) else repr(v)


def split_ending(line):
    for e in ('\r\n', '\n'):
        if line.endswith(e):
            return line[:-len(e)], e
    return line, ''


def read_lines(path):
    raw = Path(path).read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw[3:].decode('utf-8') if bom else raw.decode('utf-8')
    return bom, io.StringIO(text, newline='').readlines()


def write_lines(path, bom, lines):
    data = ''.join(lines).encode('utf-8')
    Path(path).write_bytes((b'\xef\xbb\xbf' if bom else b'') + data)


def update_coefficients(factors, skill, year, write):
    report = {}
    for model in ('Adult', 'Child', 'Infant'):
        path = skill / 'data' / f'BY{year}' / f'{model.lower()}_model_factors.csv'
        bom, lines = read_lines(path)
        new, changed_cells, changed_vars = [], 0, 0
        for ln in lines:
            body, end = split_ending(ln)
            cells = body.split(',')
            var = cells[0]
            edge = factors[model].get(var)
            if edge is not None and var != 'Variable':
                cur = [float(c) for c in cells[1:6]]
                diff = sum(abs(a - b) > 1e-9 for a, b in zip(cur, edge))
                if diff:
                    changed_cells += diff
                    changed_vars += 1
                    ln = ','.join([var] + [fmt(v) for v in edge]) + end
            new.append(ln)
        have = {split_ending(ln)[0].split(',')[0] for ln in lines}
        missing = [v for v in factors[model] if v not in have]
        report[model] = (changed_vars, changed_cells, missing)
        if write and changed_cells:
            write_lines(path, bom, new)
    return report


def update_ndc(path_xlsx, skill, year, write):
    df = read_sheet(path_xlsx, 'NDC_RXC_MAPPING')
    df['RXC'] = df.RXC.str.strip()
    active = set(map(tuple, df[df.OPERATION != 'DELETE'][['NDC_CODE', 'RXC']].values))
    deleted = set(map(tuple, df[df.OPERATION == 'DELETE'][['NDC_CODE', 'RXC']].values))
    is_new = set(map(tuple, df[df.OPERATION == 'NEW'][['NDC_CODE', 'RXC']].values))
    path = skill / 'references' / 'ndc-rxc.csv'
    bom, lines = read_lines(path)
    out, ended, valid, rows = [lines[0]], 0, set(), []
    for ln in lines[1:]:
        body, end = split_ending(ln)
        if not body:
            out.append(ln)
            continue
        ndc, rxc, s, e = body.split(',')
        s, e = int(s), int(e)
        if not rxc.startswith('ACF') and (ndc, rxc) in deleted and e >= year:
            assert s < year, (ndc, rxc, s, e)
            e = year - 1
            ended += 1
            ln = f'{ndc},{rxc},{s},{e}{end}'
        if not rxc.startswith('ACF') and s <= year <= e:
            valid.add((ndc, rxc))
        out.append(ln)
        rows.append((ndc, rxc, s, e))
    add = sorted(active - valid, key=lambda k: (int(k[1]), k[0]))
    have_pair = {(r[0], r[1]) for r in rows}
    for ndc, rxc in add:
        out.append(f'{ndc},{rxc},{year},{year + 1}\n')
    assert (valid | set(add)) == active, f'BY{year} valid set != EDGE active set'
    if write:
        write_lines(path, bom, out)
    return dict(ended=ended, added=len(add), added_marked_new=len(is_new & set(add)),
                added_by_rxc=dict(sorted(Counter(r for _, r in add).items(), key=lambda kv: int(kv[0]))),
                added_pairs_with_other_year_rows=sum(1 for k in add if k in have_pair),
                edge_active=len(active), total_rows=len(out) - 1)


def update_hcpcs(path_xlsx, skill, write):
    df = read_sheet(path_xlsx, 'HCPCS_RXC_MAPPING')
    df['RXC'] = df.RXC.str.strip()
    active = set(map(tuple, df[df.OPERATION != 'DELETE'][['HCPCS_CODE', 'RXC']].values))
    path = skill / 'references' / 'hcpcs-rxc.csv'
    bom, lines = read_lines(path)
    out, removed, seen = [lines[0]], [], set()
    for ln in lines[1:]:
        body, _ = split_ending(ln)
        if not body:
            continue
        code, rxc = body.split(',')
        if not rxc.startswith('ACF') and (code, rxc) not in active:
            removed.append((code, rxc))
            continue
        seen.add((code, rxc))
        out.append(ln)
    add = sorted(active - seen, key=lambda k: (int(k[1]), k[0]))
    for code, rxc in add:
        out.append(f'{code},{rxc}\n')
    if write:
        write_lines(path, bom, out)
    return dict(removed=removed, added=add, total_rows=len(out) - 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('workbook')
    ap.add_argument('--skill-dir', default=str(DEFAULT_SKILL))
    ap.add_argument('--year', type=int, default=2026)
    ap.add_argument('--write', action='store_true', help='apply changes (default is a dry run)')
    a = ap.parse_args()
    skill = Path(a.skill_dir)
    print('WRITING' if a.write else 'DRY RUN', 'against', skill)
    factors = build_factors(a.workbook)
    for model, (vars_, cells, missing) in update_coefficients(factors, skill, a.year, a.write).items():
        print(f'{model}: {vars_} variables / {cells} cells differ from EDGE; EDGE variables not in CSV: {missing}')
    print('NDC  :', update_ndc(a.workbook, skill, a.year, a.write))
    print('HCPCS:', update_hcpcs(a.workbook, skill, a.write))


if __name__ == '__main__':
    sys.exit(main())
