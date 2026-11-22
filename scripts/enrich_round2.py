#!/usr/bin/env python3
"""Add remaining catalog identifiers, with a hard guard against duplicates.

Only adds a designation if, after normalisation, no other row of the same
dataset already carries it. A designation that would appear twice is skipped and
reported, so the catalog can never grow a new duplicate this way.

Source: the `Identifiers` column of OpenNGC, for rows already matched by
M/NGC/IC, plus the cross-IDs of the Stellarium row that already matched.

Usage:
  python scripts/enrich_round2.py
  python scripts/enrich_round2.py --apply
"""
import argparse
import csv
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
SOURCE = os.path.join(ROOT, "source_data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402
from import_sources import (  # noqa: E402
    DEEP_ORDER, format_names, load_openngc, load_stellarium, openngc_match, parse_names, read_csv, write_rows,
)

DATASETS = ["nebulae", "galaxies", "star_clusters"]
# Indexul de protectie se construieste din toate fisierele, chiar daca doar trei primesc ID-uri.
INDEX_DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "stars", "extrema"]
# Cataloage prea zgomotoase pentru Other_Names (zeci de intrari per obiect).
SKIP_SLUGS = {"sdss", "2masx", "2mass", "gaia"}


def canon(item):
    parsed = split_item(item)
    if not parsed:
        return None
    label, slug, _text, _rest = parsed
    if slug in SKIP_SLUGS:
        return None
    text = " ".join(str(item).split())
    tail = re.sub(r"\d+", lambda match: str(int(match.group())), text[len(label):].lstrip())
    return slug, f"{label} {tail}"


def index_rows(rows):
    index = {}
    for row in rows:
        for item in (row.get("Other_Names") or "").split(","):
            parsed = canon(item)
            if parsed:
                index.setdefault(parsed[1], set()).add(row["UID"])
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    by_m, by_ngc, by_ic = load_openngc()
    stellarium = load_stellarium()

    openngc_rows = read_csv(os.path.join(SOURCE, "opengc_ngc.csv"), delimiter=";")
    openngc_rows += read_csv(os.path.join(SOURCE, "opengc_addendum.csv"), delimiter=";")
    by_name = {str(row.get("Name", "")).strip().upper(): row for row in openngc_rows if row.get("Name")}

    total_added = 0
    collisions = []

    loaded = {}
    index = {}
    for dataset in INDEX_DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        loaded[dataset] = (path, reader.fieldnames, rows)
        for row in rows:
            for item in (row.get("Other_Names") or "").split(","):
                parsed = canon(item)
                if parsed:
                    index.setdefault(parsed[1], set()).add(row["UID"])

    for dataset in DATASETS:
        if dataset not in loaded:
            continue
        path, header, rows = loaded[dataset]
        added = 0
        for row in rows:
            groups, unknown = parse_names(row.get("Other_Names"))
            candidates = []

            match = openngc_match(groups, by_m, by_ngc, by_ic)
            if match:
                source_row = by_name.get(str(match.get("Name", "")).strip().upper())
                if source_row:
                    candidates.extend((source_row.get("Identifiers") or "").split(","))

            # Doar Identifiers din OpenNGC: sunt ale obiectului insusi.
            # Cross-ID-urile din Stellarium au produs duplicatele din runda trecuta.

            for candidate in candidates:
                parsed = canon(candidate)
                if not parsed:
                    continue
                key = parsed[1]
                owners = index.get(key, set())
                if row["UID"] in owners and len(owners) > 1:
                    collisions.append((dataset, key, row["UID"], sorted(owners - {row["UID"]})))
                    continue
                if row["UID"] in owners:
                    continue
                if owners:
                    collisions.append((dataset, key, row["UID"], sorted(owners)))
                    continue
                items = [i for i in (row.get("Other_Names") or "").split(",") if i.strip()]
                items.append(candidate)
                groups2, unknown2 = parse_names(",".join(items))
                row["Other_Names"] = format_names(groups2, unknown2, DEEP_ORDER)
                index.setdefault(key, set()).add(row["UID"])
                added += 1

        if args.apply and added:
            write_rows(path, header, rows)
        print(f"{dataset:<16} identifiers added: {added}")
        total_added += added

    print(f"\nTOTAL added: {total_added}")
    print(f"SKIPPED to avoid duplicating: {len(collisions)}")
    for dataset, key, uid, owners in collisions[:15]:
        print(f"  {dataset:<14} {key:<22} would join {uid:<7} but already on {owners}")

    if not args.apply:
        print("\nDRY-RUN (nothing written)")


if __name__ == "__main__":
    main()
