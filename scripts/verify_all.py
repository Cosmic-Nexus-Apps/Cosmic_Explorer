#!/usr/bin/env python3
"""One command that checks the whole catalog and its copies.

Runs every invariant we care about and prints PASS/FAIL. Exits 1 if anything fails.

  python scripts/verify_all.py
  python scripts/verify_all.py --app-root D:/projects/apps
"""
import argparse
import csv
import glob
import hashlib
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
TRANSLATIONS = os.path.join(CATALOG, "translations")
REGISTRY = os.path.join(CATALOG, "uid-registry.json")
ALIASES = os.path.join(CATALOG, "uid-aliases.json")

DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "stars", "extrema"]
COPIES = [
    "cosmic_site/public/catalog",
    "cosmic_night_atlas/cosmic-night-atlas/public/catalog",
    "cosmic_atlas_beta/src/data/catalogs",
]
LANGUAGES = ["Name_RO", "Name_DE", "Name_FR", "Name_ES", "Name_IT", "Name_PT", "Name_PL", "Name_NL"]

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    return condition


def load(dataset):
    path = os.path.join(CATALOG, dataset + ".csv")
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames or [], list(reader)


def numeric_uid(uid):
    match = re.search(r"\d+", uid or "")
    return int(match.group()) if match else -1


def numeric_id(value):
    match = re.search(r"-(\d+)(?:-[A-Z])?$", value or "")
    return int(match.group(1)) if match else -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default=os.path.dirname(ROOT))
    args = parser.parse_args()

    data = {dataset: load(dataset) for dataset in DATASETS}

    # 1. fisiere si randuri
    total = sum(len(rows) for _header, rows in data.values())
    check("catalog: 6 fisiere, randuri lizibile", all(len(rows) > 0 for _h, rows in data.values()), f"{total} obiecte")

    # 2. UID unic
    duplicates = []
    for dataset, (_header, rows) in data.items():
        seen = set()
        for row in rows:
            uid = row.get("UID", "")
            if uid in seen:
                duplicates.append(uid)
            seen.add(uid)
    check("UID unic in fiecare fisier", not duplicates, f"duplicate: {duplicates[:5]}" if duplicates else "")

    # 3. ordine ID + ID = pozitia
    out_of_order = []
    wrong_position = 0
    for dataset, (_header, rows) in data.items():
        if dataset == "extrema":
            continue
        previous = -1
        for index, row in enumerate(rows, start=1):
            value = numeric_id(row.get("ID", ""))
            if value < previous:
                out_of_order.append(row.get("ID", ""))
            previous = value
            if value != index:
                wrong_position += 1
    check("ID crescator", not out_of_order, f"ex: {out_of_order[:3]}")
    check("ID = pozitia in catalog", wrong_position == 0, f"{wrong_position} rânduri diferite")

    # 4. registru
    with open(REGISTRY, encoding="utf-8") as fh:
        import json
        registry = json.load(fh)
    known = {uid for dataset, rows in registry.get("datasets", {}).items() for uid in rows}
    current = {row.get("UID") for _h, rows in data.values() for row in rows}
    missing = sorted(current - known)
    retired_present = sorted(set(registry.get("retired", {})) & current)
    check("registru acopera toate UID-urile", not missing, f"noi: {missing[:5]}")
    check("niciun UID retras nu reapare", not retired_present, f"{retired_present[:5]}")
    check("registru version 2", registry.get("version") == 2, str(registry.get("version")))

    # 5. aliasuri
    with open(ALIASES, encoding="utf-8") as fh:
        import json as json2
        aliases = json2.load(fh)
    broken = [old for old, new in aliases.items() if new not in current]
    check("aliasurile trimit catre UID-uri existente", not broken, f"{broken[:5]}")
    check("aliasurile nu reintroduc UID retras", not (set(aliases) & current), "")

    # 6. traduceri
    stale = []
    for path in glob.glob(os.path.join(TRANSLATIONS, "*.csv")):
        for row in csv.DictReader(open(path, encoding="utf-8")):
            uid = row["UID"]
            dataset = next((d for d, (_h, rows) in data.items() if any(r.get("UID") == uid for r in rows)), None)
            if dataset is None:
                stale.append(f"{uid} inexistent")
                continue
            name = next(r.get("Primary_Name", "") for r in data[dataset][1] if r.get("UID") == uid)
            if (row.get("Name_EN") or "").strip() != (name or "").strip():
                stale.append(f"{uid} Name_EN diferit")
    check("traduceri sincronizate cu numele din catalog", not stale, f"{stale[:3]}")

    # 7. copiile din aplicatii
    canonical = {}
    for dataset in DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        canonical[dataset] = hashlib.md5(open(path, "rb").read()).hexdigest()
    for copy in COPIES:
        folder = os.path.join(args.app_root, copy)
        if not os.path.isdir(folder):
            check(f"copie {copy}", False, "folder lipsa")
            continue
        different = []
        for dataset in DATASETS:
            target = os.path.join(folder, dataset + ".csv")
            if not os.path.exists(target):
                different.append(f"{dataset}: lipsa")
            elif hashlib.md5(open(target, "rb").read()).hexdigest() != canonical[dataset]:
                different.append(f"{dataset}: diferit")
        check(f"copie {copy.split('/')[0]}", not different, ", ".join(different[:3]))

    # 8. indexul by-designation
    index_rows = 0
    index_files = glob.glob(os.path.join(CATALOG, "by-designation", "*.csv"))
    for path in index_files:
        index_rows += max(0, sum(1 for _ in open(path, encoding="utf-8")) - 1)
    check("by-designation generat", len(index_files) > 40, f"{len(index_files)} fisiere, {index_rows} intrari")

    print("Catalog verification")
    failures = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    print(f"\n{len(results) - failures}/{len(results)} verificari trecute")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
