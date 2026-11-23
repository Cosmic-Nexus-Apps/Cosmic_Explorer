#!/usr/bin/env python3
"""Build docs/history.md: v1 vs v2, summary first, then every column.

  python scripts/catalog_audit.py
  python scripts/catalog_audit.py --compare source_data/pristine --out docs/history.md
"""
import argparse
import csv
import os
import statistics
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_designation_index import split_item  # noqa: E402

DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "stars", "extrema"]
LIST_COLUMNS = {"Other_Names"}
CONSTANT_COLUMNS = {"ID", "UID"}
DISTRIBUTION_COLUMNS = {"Recommendation_Level", "Opacity", "Type", "Nebula_Type", "Extrema_Type"}

CLOSING = """
## What was removed and why

| Item | v1 | v2 | Reason |
|---|---|---|---|
| `Is_Verified` | column in every file | **removed** | manual verification, no longer performed |
| 33 duplicate objects | separate rows | **merged** | same object twice; retired UIDs have aliases |
| 28 objects in `galaxies.csv` that were clusters or nebulae | in galaxies | **moved** where they belong | M 47, NGC 4147, NGC 5189 and others |
| 182 nebulae with `DEC = 0` | on the equator | **real declination** | recovered from Stellarium |
| `99` as "unknown" in extrema | `99` | `0` | one convention across the catalog |

## Where to find v1

The `v1` branch of this repository contains exactly the old data: six CSVs and the translations,
24,924 objects. Tag: `v1`.
"""


def read(folder, dataset):
    path = os.path.join(folder, dataset + ".csv")
    if not os.path.exists(path):
        return [], []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames or [], list(reader)


def empty(value):
    return str(value or "").strip() in ("", "-", "0", "0.0")


def as_number(value):
    try:
        return float(str(value).strip())
    except Exception:
        return None


def column_stats(rows, column):
    stats = {"filled": 0, "numbers": [], "items": 0, "distribution": Counter()}
    for row in rows:
        value = row.get(column)
        if column in LIST_COLUMNS:
            items = [item for item in (value or "").split(",") if item.strip() and item.strip() != "-"]
            stats["items"] += len(items)
            if items:
                stats["filled"] += 1
            continue
        if empty(value):
            continue
        stats["filled"] += 1
        number = as_number(value)
        if number is not None:
            stats["numbers"].append(number)
        stats["distribution"][str(value).strip()] += 1
    return stats


def percent(filled, total):
    return f"{100.0 * filled / total:.1f}%" if total else "—"


def describe(column, stats, total):
    if column in CONSTANT_COLUMNS:
        return f"{stats['filled']} ({percent(stats['filled'], total)})"
    if column in LIST_COLUMNS:
        average = stats["items"] / stats["filled"] if stats["filled"] else 0
        return f"{stats['filled']} objects · {stats['items']} ID · {average:.2f}/object"
    if column in DISTRIBUTION_COLUMNS:
        values = ", ".join(f"{key}={count}" for key, count in stats["distribution"].most_common(4))
        return f"{stats['filled']} ({percent(stats['filled'], total)}) · {values}"
    if stats["numbers"]:
        return (
            f"{stats['filled']} ({percent(stats['filled'], total)}) · "
            f"min {min(stats['numbers']):g} · med {statistics.median(stats['numbers']):g} · "
            f"max {max(stats['numbers']):g}"
        )
    return f"{stats['filled']} ({percent(stats['filled'], total)})"


def signature(column, stats, total):
    if column in CONSTANT_COLUMNS:
        return "100"
    if column in LIST_COLUMNS:
        return f"{stats['items'] / stats['filled']:.2f}" if stats["filled"] else "0"
    if column in DISTRIBUTION_COLUMNS:
        return ",".join(f"{key}={count}" for key, count in stats["distribution"].most_common(6))
    share = f"{100.0 * stats['filled'] / total:.1f}" if total else "0"
    if stats["numbers"]:
        return f"{share}|{statistics.median(stats['numbers']):g}"
    return share


def canon(item):
    parsed = split_item(item)
    if not parsed:
        return None
    label = parsed[0]
    text = " ".join(str(item).split())
    return label, text


def survey(folder):
    data = {}
    shared = defaultdict(set)
    for dataset in DATASETS:
        columns, rows = read(folder, dataset)
        data[dataset] = (columns, rows)
        for row in rows:
            for item in (row.get("Other_Names") or "").split(","):
                parsed = canon(item)
                if parsed:
                    shared[parsed].add(row.get("UID"))
    return data, sum(1 for uids in shared.values() if len(uids) > 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", default=os.path.join(ROOT, "source_data", "pristine"))
    parser.add_argument("--out")
    args = parser.parse_args()

    now_data, now_shared = survey(CATALOG)
    before_data, before_shared = survey(args.compare)

    lines = ["# History — v1 vs v2", ""]
    lines.append(f"Comparison: **v1** (`source_data/pristine`) vs **v2** (`catalog/`). Regenerate with "
                 "`python scripts/catalog_audit.py`.")
    lines.append("")

    # 1. obiecte
    lines.append("## 1. Objects")
    lines.append("")
    lines.append("| Dataset | v1 | v2 | Difference |")
    lines.append("|---|---:|---:|---:|")
    total_before = total_now = 0
    for dataset in DATASETS:
        before = len(before_data.get(dataset, ([], []))[1])
        now = len(now_data.get(dataset, ([], []))[1])
        total_before += before
        total_now += now
        lines.append(f"| {dataset} | {before} | {now} | {now - before:+d} |")
    lines.append(f"| **Total** | **{total_before}** | **{total_now}** | **{total_now - total_before:+d}** |")
    lines.append("")

    # 2. identificatori
    def count_identifiers(data):
        total = 0
        named = 0
        for _dataset, (_columns, rows) in data.items():
            for row in rows:
                total += len([item for item in (row.get("Other_Names") or "").split(",")
                              if item.strip() and item.strip() != "-"])
                if not empty(row.get("Primary_Name")):
                    named += 1
        return total, named

    before_ids, before_named = count_identifiers(before_data)
    now_ids, now_named = count_identifiers(now_data)
    lines.append("## 2. Identifiers and names")
    lines.append("")
    lines.append("| Metric | v1 | v2 |")
    lines.append("|---|---:|---:|")
    lines.append(f"| Identifiers in `Other_Names` | {before_ids} | {now_ids} |")
    lines.append(f"| Objects with a proper name | {before_named} | {now_named} |")
    lines.append(f"| Designations on 2+ objects | {before_shared} | {now_shared} |")
    lines.append("")
    lines.append("\"Designations on 2+ objects\" = a catalog number that appears on more than one object. "
                 "It can be correct (M 42 is both a nebula and a cluster) or a mistake. See `catalog.md`.")
    lines.append("")

    # 3. coloane
    lines.append("## 3. Columns, per catalog")
    lines.append("")
    for dataset in DATASETS:
        columns, rows = now_data.get(dataset, ([], []))
        if not rows:
            continue
        before_columns, before_rows = before_data.get(dataset, ([], []))
        lines.append(f"### {dataset} — {len(before_rows)} → {len(rows)}")
        lines.append("")
        lines.append("| Column | v1 | v2 | Changed |")
        lines.append("|---|---|---|---|")
        for column in columns:
            now_stats = column_stats(rows, column)
            if column in before_columns:
                before_stats = column_stats(before_rows, column)
                marker = "yes" if signature(column, before_stats, len(before_rows)) != signature(column, now_stats, len(rows)) else "—"
                lines.append(
                    f"| `{column}` | {describe(column, before_stats, len(before_rows))} "
                    f"| {describe(column, now_stats, len(rows))} | {marker} |"
                )
            else:
                lines.append(f"| `{column}` | — | {describe(column, now_stats, len(rows))} | yes |")
        lines.append("")

    lines.append(CLOSING)
    text = "\n".join(lines)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"written: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
