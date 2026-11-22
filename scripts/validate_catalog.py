#!/usr/bin/env python3
"""Validate the Cosmic Explorer catalog and its UID registry.

Usage:
  python scripts/validate_catalog.py
  python scripts/validate_catalog.py --update-registry
  python scripts/validate_catalog.py --check-sort
  python scripts/validate_catalog.py --json
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
REGISTRY = os.path.join(CATALOG, "uid-registry.json")
ALIASES = os.path.join(CATALOG, "uid-aliases.json")

DATASETS = [
    ("nebulae", "N", "nebulae.csv", "translations_nebulae.csv"),
    ("galaxies", "G", "galaxies.csv", "translations_galaxies.csv"),
    ("star_clusters", "SC", "star_clusters.csv", "translations_star_clusters.csv"),
    ("galaxy_clusters", "GC", "galaxy_clusters.csv", "translations_galaxy_clusters.csv"),
    ("stars", "S", "stars.csv", "translations_stars.csv"),
    ("extrema", "X", "extrema.csv", "translations_extrema.csv"),
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def number(value):
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "-", "nan", "None", "NaN"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def display_name(row):
    """Display name: the proper name or the first alternative, so the registry stays readable."""
    primary = (row.get("Primary_Name") or "").strip()
    if primary and primary != "-":
        return primary
    for item in (row.get("Other_Names") or "").split(","):
        item = item.strip()
        if item and item != "-":
            return item
    return "-"


def build_registry():
    datasets = {}
    for key, _prefix, filename, _translations in DATASETS:
        path = os.path.join(CATALOG, filename)
        if not os.path.exists(path):
            continue
        datasets[key] = {
            row.get("UID", "").strip(): {
                "id": row.get("ID", "").strip(),
                "name": display_name(row),
            }
            for row in read_csv(path)
            if row.get("UID")
        }
    # UID-urile retrase nu se refolosesc niciodata: se pastreaza la regenerare.
    retired = {}
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as fh:
            retired.update(json.load(fh).get("retired", {}))
    if os.path.exists(ALIASES):
        with open(ALIASES, encoding="utf-8") as fh:
            for old, new in json.load(fh).items():
                retired.setdefault(old, {"merged_into": new, "date": date.today().isoformat()})
    return {
        "version": 2,
        "updated_at": date.today().isoformat(),
        "datasets": datasets,
        "retired": dict(sorted(retired.items())),
    }


def validate(check_sort=False, registry=None):
    errors = []
    warnings = []
    stats = {}

    for key, prefix, filename, translations_file in DATASETS:
        path = os.path.join(CATALOG, filename)
        if not os.path.exists(path):
            errors.append(f"{filename}: missing")
            continue

        rows = read_csv(path)
        uids = [r.get("UID", "").strip() for r in rows]
        ids = [r.get("ID", "").strip() for r in rows]
        uid_set = set(uids)
        id_set = set(ids)
        by_uid = {r.get("UID", "").strip(): r for r in rows}

        dup_uid = sorted({u for u, count in Counter(uids).items() if u and count > 1})
        dup_id = sorted({i for i, count in Counter(ids).items() if i and count > 1})
        bad_prefix = [u for u in uids if u and not re.fullmatch(prefix + r"\d+", u)]
        missing_uid = sum(1 for u in uids if not u)
        missing_id = sum(1 for i in ids if not i)
        missing_ra = 0
        missing_dec = 0
        bad_ra = 0
        bad_dec = 0
        bad_const = 0

        for row in rows:
            ra = number(row.get("RA_deg"))
            dec = number(row.get("DEC_deg"))
            if ra is None:
                missing_ra += 1
            elif ra < 0 or ra > 360:
                bad_ra += 1
            if dec is None:
                missing_dec += 1
            elif dec < -90 or dec > 90:
                bad_dec += 1
            if not str(row.get("Constellation", "")).strip():
                bad_const += 1
            for column in ("Size_W_arcmin", "Size_H_arcmin", "Magnitude", "Surface_Brightness"):
                if column in row:
                    value = number(row.get(column))
                    if value is None:
                        continue
                    if column in ("Magnitude", "Surface_Brightness") and value == 99:
                        continue  # sentinel pentru necunoscut
                    if column in ("Size_W_arcmin", "Size_H_arcmin") and value < 0:
                        errors.append(f"{filename}: {row.get('UID')} {column} negativ ({value})")
                    if column == "Magnitude" and (value < -30 or value > 30):
                        errors.append(f"{filename}: {row.get('UID')} Magnitude out of range ({value})")
                    if column == "Surface_Brightness" and (value < -30 or value > 40):
                        errors.append(f"{filename}: {row.get('UID')} Surface_Brightness out of range ({value})")

        if missing_uid:
            errors.append(f"{filename}: {missing_uid} UID missing")
        if dup_uid:
            errors.append(f"{filename}: UID duplicate: {dup_uid[:5]}")
        if bad_prefix:
            errors.append(f"{filename}: UID with wrong prefix: {bad_prefix[:5]}")
        if missing_id:
            errors.append(f"{filename}: {missing_id} ID missing")
        if dup_id:
            errors.append(f"{filename}: ID duplicate: {dup_id[:5]}")
        if bad_ra:
            errors.append(f"{filename}: {bad_ra} RA out of range")
        if bad_dec:
            errors.append(f"{filename}: {bad_dec} DEC out of range")
        if bad_const:
            errors.append(f"{filename}: {bad_const} missing constellations")

        new_uids = []
        if registry:
            stored = registry.get("datasets", {}).get(key, {})
            for uid, entry in stored.items():
                current = by_uid.get(uid)
                if current is None:
                    errors.append(f"{filename}: UID {uid} disappeared from the registry")
                elif entry.get("id") and entry["id"] != current.get("ID", "").strip():
                    errors.append(f"{filename}: UID {uid} has a different ID than in the registry")
            new_uids = sorted(uid_set - set(stored))
            if new_uids:
                warnings.append(f"{filename}: new UID, registry update required: {new_uids[:5]}")

        translations_path = os.path.join(CATALOG, "translations", translations_file)
        if os.path.exists(translations_path):
            translation_rows = read_csv(translations_path)
            translation_uids = [r.get("UID", "").strip() for r in translation_rows]
            unknown = sorted(set(translation_uids) - uid_set)
            if unknown:
                errors.append(f"{translations_file}: UID not found in the catalog: {unknown[:5]}")
        else:
            warnings.append(f"{translations_file}: missing")

        if check_sort and key != "extrema":
            def id_number(row):
                match = re.search(r"-(\d+)(?:-[OG])?$", str(row.get("ID", "")))
                return (int(match.group(1)) if match else 10**9, row.get("UID", ""))

            violations = []
            for index in range(len(rows) - 1):
                if id_number(rows[index]) > id_number(rows[index + 1]):
                    violations.append(
                        f"{rows[index].get('UID')} before {rows[index + 1].get('UID')}"
                    )
            if violations:
                warnings.append(f"{filename}: {len(violations)} abateri de ordine ID; primele: {violations[:3]}")

        stats[key] = {
            "rows": len(rows),
            "unique_uids": len(uid_set),
            "duplicate_uids": len(dup_uid),
            "new_uids": len(new_uids),
            "missing_ra": missing_ra,
            "missing_dec": missing_dec,
            "missing_constellation": bad_const,
            "translations": os.path.exists(translations_path),
        }

    return stats, errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-registry", action="store_true")
    parser.add_argument("--check-sort", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    registry = None
    if os.path.exists(REGISTRY) and not args.update_registry:
        with open(REGISTRY, encoding="utf-8") as fh:
            registry = json.load(fh)

    stats, errors, warnings = validate(check_sort=args.check_sort, registry=registry)

    if args.update_registry:
        data = build_registry()
        os.makedirs(CATALOG, exist_ok=True)
        with open(REGISTRY, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"Registru actualizat: {REGISTRY}")

    if args.json:
        print(json.dumps({"stats": stats, "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
    else:
        print("Catalog validation")
        for key, item in stats.items():
            print(
                f"  {key:16} rows={item['rows']:6} unique={item['unique_uids']:6} "
                f"dup={item['duplicate_uids']:2} new={item['new_uids']:2} "
                f"missing_ra={item['missing_ra']:3} missing_dec={item['missing_dec']:4}"
            )
        if errors:
            print(f"\nERRORS ({len(errors)})")
            for error in errors[:20]:
                print("  -", error)
        if warnings:
            print(f"\nWARNINGS ({len(warnings)})")
            for warning in warnings[:20]:
                print("  -", warning)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
