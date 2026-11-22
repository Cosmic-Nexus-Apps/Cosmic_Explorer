#!/usr/bin/env python3
"""Resolve designations that sit on more than one row, using source positions.

For Sh2, LDN, LBN, B, C, Cr, Mel and MWSC we know where the catalog object is.
The row closest to that position keeps the designation; the others lose it.
If a row is left with no designation at all, it is reported as an orphan.

Usage:
  python scripts/resolve_shared_designations.py
  python scripts/resolve_shared_designations.py --apply
"""
import argparse
import csv
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from import_sources import (  # noqa: E402
    DEEP_ORDER, format_names, load_mwsc, load_stellarium, number, parse_names, write_rows,
)

DATASETS = ["nebulae", "star_clusters", "galaxies"]
SOURCE_KEY = {
    "sharpless": "Sh2", "ldn": "LDN", "lbn": "LBN", "barnard": "B",
    "caldwell": "C", "collinder": "Cr", "melotte": "Mel",
}
TOLERANCE_ARCMIN = 60.0


def canon_key(item):
    parsed = split_item(item)
    if not parsed:
        return None
    label, slug, _text, _rest = parsed
    text = " ".join(str(item).split())
    tail = text[len(label):].lstrip()
    # Semnul conteaza la MCG (+07-02-016 nu e -07-02-016).
    normalized = re.sub(r"\d+", lambda match: str(int(match.group())), tail)
    return slug, normalized, f"{label} {normalized}"


def arcmin(ra1, de1, ra2, de2):
    d1, d2 = math.radians(de1), math.radians(de2)
    dra = math.radians(ra1 - ra2)
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(dra / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(h))) * 60.0


def source_position(slug, value, stellarium, mwsc):
    if slug == "mwsc":
        entry = mwsc.get(value.lstrip("0") or "0")
        return (entry[0], entry[1]) if entry else None
    key = SOURCE_KEY.get(slug)
    if not key:
        return None
    row = stellarium.get(key, {}).get(value)
    if not row:
        return None
    ra, dec = number(row[1]), number(row[2])
    return (ra, dec) if ra is not None and dec is not None else None


def strip_designation(row, key):
    items = [item.strip() for item in (row.get("Other_Names") or "").split(",")]
    kept = [item for item in items if item and (canon_key(item) or (None, None, None))[2] != key]
    groups, unknown = parse_names(",".join(kept))
    return format_names(groups, unknown, DEEP_ORDER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    stellarium = load_stellarium()
    mwsc = load_mwsc()

    resolved = []
    unknown = []
    for dataset in DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            rows = list(reader)

        by_key = {}
        for row in rows:
            for item in (row.get("Other_Names") or "").split(","):
                parsed = canon_key(item)
                if parsed:
                    by_key.setdefault(parsed[2], []).append(row)

        changed = False
        for key, group in sorted(by_key.items()):
            unique = {row["UID"]: row for row in group}
            if len(unique) < 2:
                continue
            slug, value, _ = canon_key(key)
            position = source_position(slug, value, stellarium, mwsc)
            if position is None:
                unknown.append((dataset, key, list(unique)))
                continue
            distances = []
            for row in unique.values():
                ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
                if ra is None or dec is None:
                    continue
                distances.append((arcmin(ra, dec, position[0], position[1]), row))
            if not distances:
                unknown.append((dataset, key, list(unique)))
                continue
            distances.sort()
            best, owner = distances[0]
            if best > TOLERANCE_ARCMIN:
                unknown.append((dataset, key, list(unique)))
                continue
            for distance, row in distances[1:]:
                resolved.append((dataset, key, row["UID"], owner["UID"], round(best, 1), round(distance, 1)))
                row["Other_Names"] = strip_designation(row, key)
                changed = True

        if args.apply and changed:
            write_rows(path, header, rows)
            orphans = [
                row["UID"] for row in rows
                if (row.get("Other_Names") or "").strip() in ("", "-")
            ]
            for uid in orphans:
                print(f"  ORPHAN after cleanup: {dataset} {uid}")

    print(f"RESOLVED by source position: {len(resolved)}")
    for dataset, key, uid, owner, owner_d, row_d in resolved:
        print(f"  {dataset:<14} {key:<12} removed from {uid:<7} → kept on {owner:<7} ({owner_d}' vs {row_d}')")
    print(f"\nUNRESOLVED (no source position): {len(unknown)}")
    for dataset, key, uids in unknown:
        print(f"  {dataset:<14} {key:<12} {uids}")

    print("\nAPPLIED" if args.apply else "\nDRY-RUN (nothing written)")


if __name__ == "__main__":
    main()
