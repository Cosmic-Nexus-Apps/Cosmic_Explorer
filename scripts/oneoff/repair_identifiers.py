#!/usr/bin/env python3
"""Repair identifiers and star names that enrichment attached to the wrong object.

Two fixes, both driven by the pristine catalog kept in source_data/pristine:

1. A designation that exists on only one row in the pristine catalog must not
   end up on several rows. Every extra row loses it. This removes the
   NGC 7000-style duplicates that the cross-match created.
2. Star proper names come from HYG when the position match is under 2 arcsec,
   overwriting names that were attached to the wrong star (Merak on Alkaid).

Usage:
  python scripts/repair_identifiers.py
  python scripts/repair_identifiers.py --apply
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
PRISTINE = os.path.join(ROOT, "source_data", "pristine")
SOURCE = os.path.join(ROOT, "source_data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from import_sources import (  # noqa: E402
    DEEP_ORDER, format_names, load_openngc, number, openngc_match, parse_names, read_csv, write_rows,
)

DEEP = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters"]

ADJECTIVE = {"B": "B", "Sh2": "Sh2", "LDN": "LDN", "LBN": "LBN", "Cr": "Cr", "Mel": "Mel"}


def canon(item):
    """(slug, cheie canonica) — 'C 020' si 'C 20' dau aceeasi cheie."""
    parsed = split_item(item)
    if not parsed:
        return None
    label, slug, _text, rest = parsed
    normalized = re.sub(r"\d+", lambda match: str(int(match.group())), rest)
    return slug, f"{label} {normalized}"


def designation_keys(row):
    keys = set()
    for item in (row.get("Other_Names") or "").split(","):
        parsed = canon(item)
        if parsed:
            keys.add(parsed[1])
    return keys


def strip_designation(row, key):
    items = [item.strip() for item in (row.get("Other_Names") or "").split(",")]
    kept = [item for item in items if item and (canon(item) or (None, None))[1] != key]
    groups, unknown = parse_names(",".join(kept))
    return format_names(groups, unknown, DEEP_ORDER)


def repair_designations(dataset, current, pristine, apply_changes):
    current_index = {}
    for row in current:
        for key in designation_keys(row):
            current_index.setdefault(key, []).append(row["UID"])
    pristine_index = {}
    for row in pristine:
        for key in designation_keys(row):
            pristine_index.setdefault(key, []).append(row["UID"])

    removed = []
    for key, uids in current_index.items():
        if len(set(uids)) < 2:
            continue
        keep = set(pristine_index.get(key, []))
        if len(keep) >= len(set(uids)):
            continue  # era deja partajata in original
        for uid in set(uids) - keep:
            row = next(item for item in current if item["UID"] == uid)
            row["Other_Names"] = strip_designation(row, key)
            removed.append((dataset, key, uid, sorted(keep)))
    return removed


def repair_added_names(dataset, current, pristine, indexes, apply_changes):
    """A name added from OpenNGC stays only while the object still matches."""
    by_m, by_ngc, by_ic = indexes
    original = {row["UID"]: (row.get("Primary_Name") or "").strip() for row in pristine}
    cleared = []
    for row in current:
        name = (row.get("Primary_Name") or "").strip()
        if not name or name == "-":
            continue
        if original.get(row["UID"], "-") not in ("", "-"):
            continue  # name that already existed in the catalog
        groups, _ = parse_names(row.get("Other_Names"))
        if openngc_match(groups, by_m, by_ngc, by_ic):
            continue
        cleared.append((dataset, row["UID"], name))
        if apply_changes:
            row["Primary_Name"] = "-"
    return cleared


def repair_mwsc_distances(current, apply_changes):
    """Distance from MWSC is valid only where the row sits near the MWSC centre."""
    path = os.path.join(SOURCE, "mwsc.tsv")
    if not os.path.exists(path):
        return []
    table = {}
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) < 7 or not cells[0].strip().isdigit():
                continue
            try:
                ra, dec, parsecs = float(cells[3]), float(cells[4]), float(cells[6])
            except ValueError:
                continue
            table[cells[0].strip().lstrip("0") or "0"] = (ra, dec, round(parsecs * 3.26156))

    def centre_distance(row, position):
        ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
        if ra is None or dec is None:
            return None
        d1, d2 = math.radians(dec), math.radians(position[1])
        dra = math.radians(ra - position[0])
        h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(dra / 2) ** 2
        return math.degrees(2 * math.asin(math.sqrt(h))) * 60.0

    cleared = []
    for row in current:
        numbers = []
        for item in (row.get("Other_Names") or "").split(","):
            parsed = split_item(item)
            if parsed and parsed[1] == "mwsc":
                numbers.append(parsed[3].lstrip("0") or "0")
        positions = [table[value] for value in numbers if value in table]
        if not positions:
            continue
        distances = [position[2] for position in positions]
        near = False
        for position in positions:
            offset = centre_distance(row, position)
            if offset is not None and offset <= 60:
                near = True
                break
        if near:
            continue
        current_distance = number(row.get("Distance_ly")) or 0
        if int(current_distance) in distances:
            cleared.append((row["UID"], row["Primary_Name"], int(current_distance)))
            if apply_changes:
                row["Distance_ly"] = "0"
    return cleared


def repair_star_names(current, apply_changes):
    path = os.path.join(SOURCE, "hygdata_v41.csv")
    if not os.path.exists(path):
        return [], 0
    hyg = read_csv(path)
    grid = {}
    for row in hyg:
        ra_hours, dec = number(row.get("ra")), number(row.get("dec"))
        if ra_hours is None or dec is None:
            continue
        ra = ra_hours * 15.0
        grid.setdefault((math.floor(ra / 0.1), math.floor(dec / 0.1)), []).append((ra, dec, row))

    changed = []
    hyg_name = {}
    for row in current:
        ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
        if ra is None or dec is None:
            continue
        cx, cy = math.floor(ra / 0.1), math.floor(dec / 0.1)
        best, bestd = None, 1e9
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for cra, cdec, candidate in grid.get((cx + dx, cy + dy), []):
                    distance = (cra - ra) ** 2 + (cdec - dec) ** 2
                    if distance < bestd:
                        bestd, best = distance, candidate
        if best is None or bestd > (2.0 / 3600.0) ** 2:
            continue
        proper = (best.get("proper") or "").strip()
        if proper:
            hyg_name[row["UID"]] = proper
            if (row.get("Primary_Name") or "").strip() != proper:
                changed.append((row["UID"], row.get("Primary_Name"), proper))
                if apply_changes:
                    row["Primary_Name"] = proper

    # A name that appears on two stars stays only on the one HYG confirms;
    # if HYG confirms it on neither, we leave it alone (no guessing).
    effective = {}
    for row in current:
        name = hyg_name.get(row["UID"], (row.get("Primary_Name") or "").strip())
        effective[row["UID"]] = name
    by_name = {}
    for row in current:
        name = effective[row["UID"]]
        if name and name != "-":
            by_name.setdefault(name, []).append(row)
    cleared = []
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        confirmed = [row for row in group if hyg_name.get(row["UID"]) == name]
        if not confirmed:
            continue
        for row in group:
            if row in confirmed:
                continue
            cleared.append((row["UID"], name, "-"))
            if apply_changes:
                row["Primary_Name"] = "-"
    changed.extend(cleared)
    return changed, len(current)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--pristine", default=PRISTINE)
    args = parser.parse_args()

    if not os.path.isdir(args.pristine):
        raise SystemExit(f"Missing the pristine catalog: {args.pristine}")

    total_removed = []
    indexes = load_openngc()
    total_names = []
    for dataset in DEEP:
        path = os.path.join(CATALOG, dataset + ".csv")
        pristine_path = os.path.join(args.pristine, dataset + ".csv")
        if not (os.path.exists(path) and os.path.exists(pristine_path)):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            current = list(reader)
        pristine = list(csv.DictReader(open(pristine_path, newline="", encoding="utf-8")))
        removed = repair_designations(dataset, current, pristine, args.apply)
        names = repair_added_names(dataset, current, pristine, indexes, args.apply)
        total_removed.extend(removed)
        total_names.extend(names)
        if args.apply and (removed or names):
            write_rows(path, header, current)

    print(f"IDENTIFIERS REMOVED: {len(total_removed)}")
    for dataset, designation, uid, keep in total_removed:
        print(f"  {dataset:<14} {designation:<14} removed from {uid:<7} (kept on {keep})")

    print(f"\nADDED NAMES DROPPED (not confirmed): {len(total_names)}")
    for dataset, uid, name in total_names:
        print(f"  {dataset:<14} {uid:<7} {name}")

    stars_path = os.path.join(CATALOG, "stars.csv")
    if os.path.exists(stars_path):
        with open(stars_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            stars = list(reader)
        changed, total = repair_star_names(stars, args.apply)
        if args.apply and changed:
            write_rows(stars_path, header, stars)
        print(f"\nSTAR NAMES CORRECTED: {len(changed)} of {total}")
        for uid, before, after in changed[:20]:
            print(f"  {uid:<7} {before:<18} -> {after}")

    clusters_path = os.path.join(CATALOG, "star_clusters.csv")
    if os.path.exists(clusters_path):
        with open(clusters_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            clusters = list(reader)
        cleared = repair_mwsc_distances(clusters, args.apply)
        if args.apply and cleared:
            write_rows(clusters_path, header, clusters)
        print(f"\nWRONG MWSC DISTANCES (centre >60'): {len(cleared)}")
        for uid, name, distance in cleared[:10]:
            print(f"  {uid:<7} {name[:26]:<28} {distance} ly scos")

    print("\nAPPLIED" if args.apply else "\nDRY-RUN (nothing written)")


if __name__ == "__main__":
    main()
