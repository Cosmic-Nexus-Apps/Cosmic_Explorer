#!/usr/bin/env python3
"""Check the translation files against the catalog.

Three checks that catch the usual drift:
  1. Name_EN must match the current Primary_Name (otherwise the translation is stale).
  2. Every UID must exist and appear once.
  3. Which language cells are still empty.

  python scripts/translations_audit.py
"""
import csv
import glob
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
TRANSLATIONS = os.path.join(CATALOG, "translations")

LANGUAGES = ["Name_RO", "Name_DE", "Name_FR", "Name_ES", "Name_IT", "Name_PT", "Name_PL", "Name_NL"]
DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "stars", "extrema"]

names = {}
for dataset in DATASETS:
    path = os.path.join(CATALOG, dataset + ".csv")
    if not os.path.exists(path):
        continue
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            names[row["UID"]] = (dataset, (row.get("Primary_Name") or "").strip())

stale = []
missing_uid = []
duplicates = []
seen = set()
problems = 0

print("Translation audit")
for path in sorted(glob.glob(os.path.join(TRANSLATIONS, "*.csv"))):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    empty = {}
    for row in rows:
        uid = row["UID"]
        if uid in seen:
            duplicates.append(uid)
        seen.add(uid)
        dataset, name = names.get(uid, (None, None))
        if dataset is None:
            missing_uid.append(uid)
            continue
        if (row.get("Name_EN") or "").strip() != name:
            stale.append((uid, name, row.get("Name_EN", "")))
        for language in LANGUAGES:
            if not str(row.get(language, "")).strip():
                empty[language] = empty.get(language, 0) + 1
    gaps = " ".join(f"{language[5:]}={count}" for language, count in sorted(empty.items()))
    print(f"  {os.path.basename(path):36} {len(rows):4} rows" + (f" | empty: {gaps}" if gaps else " | complete"))

print()
for uid, current, stored in stale:
    print(f"  STALE {uid}: Name_EN '{stored}' != catalog '{current}'")
for uid in missing_uid:
    print(f"  MISSING UID in catalog: {uid}")
for uid in duplicates:
    print(f"  DUPLICATE row: {uid}")
problems = len(stale) + len(missing_uid) + len(duplicates)
print(f"\nproblems: {problems}")
sys.exit(1 if problems else 0)
