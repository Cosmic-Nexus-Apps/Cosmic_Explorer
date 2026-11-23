#!/usr/bin/env python3
"""Move objects that sit in `galaxies.csv` but are really clusters or nebulae.

A galaxy row that shares a catalog designation with a star cluster or a nebula
and sits within 10 arcmin of it is the same object filed twice. The galaxy row is
merged into the correct one and its UID is retired (journal entries keep working
through uid-aliases.json).

Matches farther than 10 arcmin are only reported: there the designation, not the
row, is probably wrong.

Usage:
  python scripts/resolve_cross_dataset.py
  python scripts/resolve_cross_dataset.py --apply
"""
import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog")
ALIASES = os.path.join(CATALOG, "uid-aliases.json")
REGISTRY = os.path.join(CATALOG, "uid-registry.json")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from dedupe_catalog import merge  # noqa: E402
from import_sources import number, write_rows  # noqa: E402

TOLERANCE_ARCMIN = 10.0
TARGETS = ("star_clusters", "nebulae")


def canon(item):
    parsed = split_item(item)
    if not parsed:
        return None
    label = parsed[0]
    text = " ".join(str(item).split())
    tail = re.sub(r"\d+", lambda m: str(int(m.group())), text[len(label):].lstrip())
    return f"{label} {tail}"


def separation(a, b):
    ra1, de1 = number(a.get("RA_deg")), number(a.get("DEC_deg"))
    ra2, de2 = number(b.get("RA_deg")), number(b.get("DEC_deg"))
    if None in (ra1, de1, ra2, de2):
        return None
    d1, d2 = math.radians(de1), math.radians(de2)
    dra = math.radians(ra1 - ra2)
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(dra / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(h))) * 60.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--tolerance", type=float, default=TOLERANCE_ARCMIN)
    args = parser.parse_args()
    tolerance = args.tolerance

    loaded = {}
    index = {}
    for dataset in ("galaxies",) + TARGETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        loaded[dataset] = (path, reader.fieldnames, rows)
        if dataset in TARGETS:
            for row in rows:
                for item in (row.get("Other_Names") or "").split(","):
                    key = canon(item)
                    if key:
                        index.setdefault(key, []).append((dataset, row))

    merged = []
    far = []
    for galaxy in loaded["galaxies"][2]:
        for item in (galaxy.get("Other_Names") or "").split(","):
            key = canon(item)
            if not key:
                continue
            for dataset, other in index.get(key, []):
                distance = separation(galaxy, other)
                if distance is None:
                    continue
                if distance <= tolerance:
                    merged.append((galaxy, dataset, other, distance, key))
                elif distance < tolerance * 6:
                    far.append((galaxy, dataset, other, distance, key))

    seen = set()
    unique = []
    for galaxy, dataset, other, distance, key in sorted(merged, key=lambda item: item[3]):
        if galaxy["UID"] in seen:
            continue
        seen.add(galaxy["UID"])
        unique.append((galaxy, dataset, other, distance, key))

    print(f"TO MOVE into cluster/nebula: {len(unique)}")
    for galaxy, dataset, other, distance, key in unique:
        print(f"  {galaxy['UID']:<7} ({key}) -> {dataset:<14} {other['UID']:<7} {other['Primary_Name'][:22]:24} {distance:.1f}'")

    print(f"\nTO REVIEW (10'-60'): {len(far)}")
    for galaxy, dataset, other, distance, key in far:
        print(f"  {galaxy['UID']:<7} ({key}) vs {dataset:<14} {other['UID']:<7} {distance:.1f}'")

    if not args.apply:
        print("\nDRY-RUN (nothing written)")
        return

    touched = set()
    for galaxy, dataset, other, _distance, _key in unique:
        merge(other, galaxy)
        distance_ly = str(other.get("Distance_ly") or "").strip()
        if distance_ly in ("", "0", "0.0", "-") and number(galaxy.get("Distance_Mly")):
            other["Distance_ly"] = f"{number(galaxy['Distance_Mly']) * 1000000:.0f}"
        touched.add(dataset)

    for dataset in touched:
        path, header, rows = loaded[dataset]
        write_rows(path, header, rows)

    retired_map = {galaxy["UID"]: other["UID"] for galaxy, _ds, other, _d, _k in unique}
    path, header, rows = loaded["galaxies"]
    write_rows(path, header, [row for row in rows if row["UID"] not in retired_map])

    aliases = {}
    if os.path.exists(ALIASES):
        with open(ALIASES, encoding="utf-8") as fh:
            aliases = json.load(fh)
    aliases.update(retired_map)
    with open(ALIASES, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(aliases.items())), fh, indent=2)
        fh.write("\n")

    registry = json.load(open(REGISTRY, encoding="utf-8")) if os.path.exists(REGISTRY) else {}
    registry.setdefault("retired", {})
    for old, new in retired_map.items():
        registry["retired"][old] = {"dataset": "galaxies", "merged_into": new, "date": date.today().isoformat()}
    with open(REGISTRY, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nAPPLIED: {len(retired_map)} rows moved, {len(aliases)} aliases")


if __name__ == "__main__":
    main()
