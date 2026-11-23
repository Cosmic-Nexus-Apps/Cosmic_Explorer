#!/usr/bin/env python3
"""Sort Cosmic Explorer CSVs canonically.

Order: area desc -> magnitude asc (0/unknown last; dark: opacity desc)
       -> constellation asc -> UID asc.
IDs are never regenerated; UIDs are never touched.

Usage:
  python scripts/sort_catalog.py            # dry-run
  python scripts/sort_catalog.py --apply
  python scripts/sort_catalog.py --json
"""
import argparse
import csv
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")

DATASETS = [
    ("nebulae", "nebulae.csv"),
    ("galaxies", "galaxies.csv"),
    ("star_clusters", "star_clusters.csv"),
    ("galaxy_clusters", "galaxy_clusters.csv"),
    ("stars", "stars.csv"),
    ("extrema", "extrema.csv"),
]


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


def sort_key_area(row):
    area = (number(row.get("Size_W_arcmin")) or 0) * (number(row.get("Size_H_arcmin")) or 0)
    dark = str(row.get("Nebula_Type", "")).upper() == "DARK_NEBULA"
    if dark:
        secondary = -(number(row.get("Opacity")) or 0)
    else:
        magnitude = number(row.get("Magnitude"))
        secondary = 999.0 if magnitude is None or magnitude == 0 or magnitude >= 90 else magnitude
    return (
        -area,
        secondary,
        str(row.get("Constellation", "")),
        number(row.get("RA_deg")) or 0.0,
        number(row.get("DEC_deg")) or 0.0,
        row.get("UID", ""),
    )


def sort_key_magnitude(row):
    """Stelele nu au arie: se sorteaza dupa magnitudine, apoi dupa pozitie."""
    magnitude = number(row.get("Magnitude"))
    primary = 999.0 if magnitude is None or magnitude == 0 or magnitude >= 90 else magnitude
    return (
        primary,
        number(row.get("RA_deg")) or 0.0,
        number(row.get("DEC_deg")) or 0.0,
        row.get("UID", ""),
    )


def sort_key_id(row):
    match = re.search(r"-(\d+)(?:-[OG])?$", str(row.get("ID", "")))
    return (int(match.group(1)) if match else 10**9, row.get("UID", ""))


ID_PATTERN = re.compile(r"^(CE-[A-Z]+-)(\d+)(-[A-Z])?$")


def renumber(rows):
    """ID-ul este pozitia in catalog: se renumeroteaza dupa ordinea noua.

    UID-ul nu se atinge niciodata. Sufixul de subtip (CE-SC-4-O) se pastreaza.
    """
    changed = 0
    for index, row in enumerate(rows, start=1):
        match = ID_PATTERN.match(str(row.get("ID", "")))
        if not match:
            continue
        new_id = f"{match.group(1)}{index}{match.group(3) or ''}"
        if row.get("ID") != new_id:
            row["ID"] = new_id
            changed += 1
    return changed


def detect_newline(path):
    with open(path, "rb") as fh:
        return "\r\n" if b"\r\n" in fh.read(4096) else "\n"


def process(path, apply_changes, order, export_dir=None, renumber_ids=False):
    newline = detect_newline(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)

    dict_rows = [dict(zip(header, row)) for row in rows]
    if os.path.basename(path) == "extrema.csv":
        return {
            "file": os.path.basename(path),
            "rows": len(rows),
            "moved": 0,
            "first_moves": [],
            "applied": False,
            "skipped": "extrema ramane in ordinea actuala",
        }

    if order == "id":
        key = sort_key_id
    elif order == "magnitude":
        key = sort_key_magnitude
    else:
        key = sort_key_area
    ordered = sorted(dict_rows, key=key)
    renumbered = renumber(ordered) if renumber_ids else 0

    moved = sum(
        1
        for current, wanted in zip(dict_rows, ordered)
        if current.get("UID") != wanted.get("UID")
    )
    first_moves = [
        f"{current.get('UID')} -> {wanted.get('UID')}"
        for current, wanted in zip(dict_rows, ordered)
        if current.get("UID") != wanted.get("UID")
    ][:3]

    if export_dir:
        os.makedirs(export_dir, exist_ok=True)
        target = os.path.join(export_dir, os.path.basename(path))
        with open(target, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(header)
            for row in ordered:
                writer.writerow([row.get(name, "") for name in header])
        return {
            "file": os.path.basename(path),
            "rows": len(rows),
            "moved": moved,
            "first_moves": first_moves,
            "applied": False,
            "renumbered": renumbered,
            "skipped": f"scris in {target}",
        }

    if apply_changes and (moved or renumbered):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator=newline)
            writer.writerow(header)
            for row in ordered:
                writer.writerow([row.get(name, "") for name in header])

    return {
        "file": os.path.basename(path),
        "rows": len(rows),
        "moved": moved,
        "first_moves": first_moves,
        "renumbered": renumbered,
        "applied": bool(apply_changes and (moved or renumbered)),
        "skipped": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--order", choices=["id", "area", "magnitude"], default="id")
    parser.add_argument("--only", help="doar aceste fisiere, separate prin virgula")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--export", help="scrie o copie sortata in folderul dat, fara sa atinga catalogul")
    parser.add_argument("--renumber", action="store_true", help="renumeroteaza ID-urile dupa noua ordine (UID-ul rămâne)")
    args = parser.parse_args()

    only = {item.strip() for item in args.only.split(",")} if args.only else None
    results = []
    for key_name, filename in DATASETS:
        if only and key_name not in only:
            continue
        path = os.path.join(CATALOG, filename)
        if os.path.exists(path):
            results.append(process(path, args.apply, args.order, args.export, args.renumber))

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("Sort catalog" + (" (APPLY)" if args.apply else " (dry-run)") + f" order={args.order}")
        for item in results:
            suffix = f"skipped: {item['skipped']}" if item.get("skipped") else (
                "applied" if item["applied"] else ""
            )
            print(
                f"  {item['file']:22} rows={item['rows']:6} moved={item['moved']:5}"
                f" renumbered={item.get('renumbered', 0):5} {suffix}"
            )
            if item["first_moves"]:
                print("     ex:", ", ".join(item["first_moves"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
