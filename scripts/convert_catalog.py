#!/usr/bin/env python3
"""Convert one catalog CSV to JSON, or copy it, with an interactive prompt.

Only two formats exist here: csv and json. Values are copied as they are in the
CSV (strings), so nothing is reinterpreted.

Usage:
  python scripts/convert_catalog.py                 # interactive
  python scripts/convert_catalog.py --list
  python scripts/convert_catalog.py -c galaxies -f json -o galaxies_v1
"""
import argparse
import csv
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
EXPORTS = os.path.join(ROOT, "exports")

SKIP = {"uid-registry.json", "by-designation", "translations", "ATTRIBUTION.md"}


def catalogs():
    names = []
    for entry in sorted(os.listdir(CATALOG)):
        if entry in SKIP or not entry.endswith(".csv"):
            continue
        names.append(entry[:-4])
    return names


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or (default or "")


def pick_catalog(names):
    print("Which catalog?")
    for index, name in enumerate(names, start=1):
        print(f"  {index}) {name}")
    print("  0) exit")
    while True:
        choice = ask("Number")
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        print("  Invalid choice.")


def convert(name, fmt, output_name):
    source = os.path.join(CATALOG, name + ".csv")
    os.makedirs(EXPORTS, exist_ok=True)
    target = os.path.join(EXPORTS, f"{output_name}.{fmt}")
    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if fmt == "csv":
        with open(target, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        # `display_name` evita sa apara '-' in interfete: cade pe primul alt nume.
        payload = []
        for row in rows:
            name = (row.get("Primary_Name") or "").strip()
            if name in ("", "-"):
                first = (row.get("Other_Names") or "").split(",")[0].strip()
                name = first if first and first != "-" else "-"
            payload.append({"display_name": name, **row})
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    size = os.path.getsize(target) / 1024
    print(f"Written: {target}  ({len(rows)} objects, {size:.0f} KB)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("-c", "--catalog")
    parser.add_argument("-f", "--format", choices=["csv", "json"])
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    names = catalogs()
    if args.list:
        print("\n".join(names))
        return

    if not args.catalog:
        name = pick_catalog(names)
        if not name:
            return
        "Format:"
        print("  1) csv")
        print("  2) json")
        fmt = {"1": "csv", "2": "json"}.get(ask("Number", "1"))
        if not fmt:
            print("Format invalid.")
            return
        keep = ask(f"Keep the name '{name}'? (y/n)", "y").lower()
        output_name = name if keep.startswith("y") else ask("New name (without extension)")
        if not output_name:
            return
    else:
        if args.catalog not in names:
            print(f"Unknown catalog. Available: {', '.join(names)}")
            return
        name = args.catalog
        fmt = args.format or "json"
        output_name = args.output or f"{name}_{fmt}"

    convert(name, fmt, output_name)


if __name__ == "__main__":
    main()
