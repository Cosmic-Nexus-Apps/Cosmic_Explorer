#!/usr/bin/env python3
"""Recover missing declinations from the source catalogs.

182 nebulae carry DEC 0.0, which puts them on the celestial equator. The
declination is taken from the Stellarium row of the same designation
(LDN, Barnard, Sh2, LBN, Caldwell, Collinder, Melotte).

Usage:
  python scripts/fix_missing_declination.py
  python scripts/fix_missing_declination.py --apply
"""
import argparse
import csv
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from import_sources import load_stellarium, number, write_rows  # noqa: E402

SLUG_TO_SOURCE = {
    "ldn": "LDN", "barnard": "B", "sharpless": "Sh2", "lbn": "LBN",
    "caldwell": "C", "collinder": "Cr", "melotte": "Mel",
}
MISSING = ("", "0", "0.0", "0.0000", "0.00000")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    stellarium = load_stellarium()
    path = os.path.join(CATALOG, "nebulae.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        rows = list(reader)

    fixed = []
    unresolved = []
    for row in rows:
        if (row.get("DEC_deg") or "").strip() not in MISSING:
            continue
        position = None
        used = None
        for item in (row.get("Other_Names") or "").split(","):
            parsed = split_item(item)
            if not parsed:
                continue
            key = SLUG_TO_SOURCE.get(parsed[1])
            if not key:
                continue
            source = stellarium.get(key, {}).get(parsed[3])
            if not source and parsed[3][-1:].isalpha():
                # Barnard 84A foloseste pozitia lui Barnard 84.
                source = stellarium.get(key, {}).get(parsed[3][:-1].rstrip())
            if not source:
                continue
            ra, dec = number(source[1]), number(source[2])
            if ra is None or dec is None or dec == 0:
                continue
            position = (ra, dec)
            used = item.strip()
            break
        if position is None:
            unresolved.append(row["UID"])
            continue
        fixed.append((row["UID"], used, position[1]))
        if args.apply:
            row["DEC_deg"] = f"{position[1]:.5f}"
            if (row.get("RA_deg") or "").strip() in MISSING:
                row["RA_deg"] = f"{position[0]:.5f}"

    print(f"DEC recuperat: {len(fixed)}")
    for uid, designation, dec in fixed[:10]:
        print(f"  {uid:<7} din {designation:<14} DEC {dec:+.4f}")
    print(f"fara sursa: {len(unresolved)} {unresolved[:8]}")

    if args.apply:
        write_rows(path, header, rows)
        print("\nAPLICAT")
    else:
        print("\nDRY-RUN (nimic scris)")


if __name__ == "__main__":
    main()
