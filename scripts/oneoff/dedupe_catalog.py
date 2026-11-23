#!/usr/bin/env python3
"""Merge catalog rows that describe the same object twice.

Dry-run by default. A pair is merged only when the rows share a catalog
designation AND look like the same object (same proper name, or same magnitude,
or centres within 2 arcmin). Rows that share a designation but are different
objects (a parent region listing its members) are reported, never touched.

Merge rule: the better record survives (has a proper name, higher
recommendation, more filled fields), missing values are copied, Other_Names is
unioned, and the retired UID goes to uid-registry.json + uid-aliases.json so the
app can still resolve journal entries that point at it.

Usage:
  python scripts/dedupe_catalog.py
  python scripts/dedupe_catalog.py --apply
"""
import argparse
import csv
import json
import math
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, "catalog")
REGISTRY = os.path.join(CATALOG, "uid-registry.json")
ALIASES = os.path.join(CATALOG, "uid-aliases.json")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from import_sources import DEEP_ORDER, format_names, parse_names, write_rows  # noqa: E402
from find_object import normalize  # noqa: E402

DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters"]
TEXT_FIELDS = ["Primary_Name", "Other_Names", "Nebula_Type", "Type", "Extrema_Type", "Opacity"]
SKIP_MERGE = {"galaxy_clusters"}  # Other_Names lists member galaxies, so a match would be wrong


def number(value):
    try:
        return float(value)
    except Exception:
        return None


def separation(a, b):
    ra1, de1 = number(a.get("RA_deg")), number(a.get("DEC_deg"))
    ra2, de2 = number(b.get("RA_deg")), number(b.get("DEC_deg"))
    if None in (ra1, de1, ra2, de2):
        return None
    d1, d2 = math.radians(de1), math.radians(de2)
    dra = math.radians(ra1 - ra2)
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(dra / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(h))) * 60.0


def filled(row):
    return sum(1 for value in row.values() if str(value).strip() not in ("", "-", "0", "0.0"))


def same_object(a, b):
    name_a, name_b = normalize(a.get("Primary_Name")), normalize(b.get("Primary_Name"))
    if name_a and name_a != "-" and name_a == name_b:
        return "same name"
    mag_a, mag_b = number(a.get("Magnitude")), number(b.get("Magnitude"))
    if mag_a and mag_b and abs(mag_a - mag_b) <= 0.15:
        return "same magnitude"
    sep = separation(a, b)
    if sep is not None and sep <= 2:
        return f"centre la {sep:.1f}'"
    return None


def rank(row):
    return (
        1 if normalize(row.get("Primary_Name")) not in ("", "-") else 0,
        int(number(row.get("Recommendation_Level")) or 0),
        filled(row),
    )


def merge(survivor, duplicate):
    for key, value in duplicate.items():
        if key in ("UID", "ID"):
            continue
        if key == "Other_Names":
            continue
        if str(survivor.get(key, "")).strip() in ("", "-", "0", "0.0") and str(value).strip() not in ("", "-", "0", "0.0"):
            survivor[key] = value
    groups, unknown = parse_names(survivor.get("Other_Names"))
    extra, _ = parse_names(duplicate.get("Other_Names"))
    for catalog, values in extra.items():
        groups.setdefault(catalog, set()).update(values)
    survivor["Other_Names"] = format_names(groups, unknown, DEEP_ORDER)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    merges = []
    conflicts = []

    for dataset in DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            rows = list(reader)

        if dataset in SKIP_MERGE:
            continue

        retired_uids = set()
        by_designation = {}
        for row in rows:
            for item in (row.get("Other_Names") or "").split(","):
                parsed = split_item(item)
                if parsed:
                    by_designation.setdefault(parsed[2], []).append(row)

        for designation, group in sorted(by_designation.items()):
            unique = {row["UID"]: row for row in group if row["UID"] not in retired_uids}
            if len(unique) < 2:
                continue
            members = list(unique.values())
            reason = same_object(members[0], members[1])
            if not reason:
                conflicts.append((dataset, designation, [row["UID"] for row in members]))
                continue
            members.sort(key=rank, reverse=True)
            survivor = members[0]
            for duplicate in members[1:]:
                merge(survivor, duplicate)
                retired_uids.add(duplicate["UID"])
                merges.append((dataset, designation, duplicate["UID"], survivor["UID"], reason))

        if args.apply and merges:
            retired = {item[2] for item in merges if item[0] == dataset}
            rows = [row for row in rows if row["UID"] not in retired]
            write_rows(path, header, rows)

    print(f"MERGE: {len(merges)}")
    for dataset, designation, old, new, reason in merges:
        print(f"  {dataset:<14} {designation:<14} {old} -> {new}   ({reason})")
    print(f"\nCONFLICTS (shared designation, different objects): {len(conflicts)}")
    for dataset, designation, uids in conflicts:
        print(f"  {dataset:<14} {designation:<14} {uids}")

    if not args.apply:
        print("\nDRY-RUN (nothing written)")
        return

    aliases = {}
    if os.path.exists(ALIASES):
        with open(ALIASES, encoding="utf-8") as fh:
            aliases = json.load(fh)
    for dataset, _designation, old, new, _reason in merges:
        aliases[old] = new
    with open(ALIASES, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(aliases.items())), fh, indent=2)
        fh.write("\n")

    registry = {"version": 1, "updated_at": date.today().isoformat(), "datasets": {}, "retired": {}}
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as fh:
            registry = json.load(fh)
    registry.setdefault("retired", {})
    for dataset, _designation, old, new, _reason in merges:
        registry["retired"][old] = {
            "dataset": dataset,
            "merged_into": new,
            "date": date.today().isoformat(),
        }
    with open(REGISTRY, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"\nScris: {len(merges)} UID-uri retrase, {ALIASES}")


if __name__ == "__main__":
    main()
