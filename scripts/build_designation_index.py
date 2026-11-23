#!/usr/bin/env python3
"""Build per-designation index files from the canonical catalog.

Writes catalog/by-designation/<catalog>.csv with columns:
Designation, UID, ID, Dataset, Primary_Name.

One row = one designation -> one UID. The full record stays in the canonical
CSVs; this is only a lookup index. Every designation found in Other_Names gets
a file, and ESO/MCG keep their full number (ESO 56-115, not ESO 56).

Usage: python scripts/build_designation_index.py
"""
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
OUT = os.path.join(CATALOG, "by-designation")

# galaxy_clusters are indexed only by Abell: their Other_Names lists member
# galaxies, so NGC/M entries there would point at the wrong object.
DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "stars"]

# Doar familii de cataloage reale. Orice alt text din Other_Names e nume propriu
# or a phrase fragment and never becomes an index.
PREFIXES = [
    ("Collinder", "collinder"), ("Kronberger", "kronberger"), ("Ruprecht", "ruprecht"),
    ("Melotte", "melotte"), ("Trumpler", "trumpler"), ("Czernik", "czernik"),
    ("Teutsch", "teutsch"), ("Dolidze", "dolidze"), ("Berkeley", "berkeley"),
    ("Barnard", "barnard"), ("Alessi", "alessi"), ("Haffner", "haffner"),
    ("vdBergh-Hagen", "vdberghhagen"), ("Dutra-Bica", "dutrabica"),
    ("Gaia DR3", "gaia"), ("Gaia DR2", "gaia"), ("Gaia DR1", "gaia"),
    ("Sh2", "sharpless"), ("Loden", "loden"), ("LBN", "lbn"), ("LDN", "ldn"),
    ("DBSB", "dbsb"), ("BDSB", "bdsb"), ("Abell", "abell"), ("MWSC", "mwsc"),
    ("2MASS", "2mass"), ("ASCC", "ascc"), ("UGCA", "ugca"), ("SAI", "sai"),
    ("IRAS", "iras"), ("TYC", "tycho"), ("Cederblad", "cederblad"), ("Ced", "cederblad"),
    ("RCW", "rcw"), ("HCG", "hcg"), ("FSR", "fsr"), ("MCG", "mcg"),
    ("PGC", "pgc"), ("UGC", "ugc"), ("ESO", "eso"), ("NGC", "ngc"), ("IC", "ic"),
    ("Arp", "arp"), ("Cr", "collinder"), ("Mel", "melotte"), ("Gl", "gliese"),
    ("GJ", "gliese"), ("SAO", "sao"), ("HD", "hd"), ("HR", "hr"), ("HIP", "hip"),
    ("Stock", "stock"), ("Pismis", "pismis"), ("King", "king"), ("Terzan", "terzan"),
    ("Lynga", "lynga"), ("Bochum", "bochum"), ("Basel", "basel"), ("Hogg", "hogg"),
    ("Koposov", "koposov"), ("vdB", "vdberg"),
    ("M", "messier"), ("C", "caldwell"), ("B", "barnard"),
]
PREFIXES.sort(key=lambda item: -len(item[0]))


def split_item(item):
    """Returneaza (eticheta, slug, desemnare, cheie_numerica) sau None."""
    text = " ".join(str(item).split())
    if not text or text == "-":
        return None
    upper = text.upper()
    for label, slug in PREFIXES:
        if not upper.startswith(label.upper()):
            continue
        rest = text[len(label):].lstrip(" -+")
        if rest and (rest[0].isdigit() or label == "2MASS"):
            return label, slug, text, rest
    return None


def sort_key(rest):
    numbers = tuple(int(value) for value in re.findall(r"\d+", rest))
    return numbers or (0,)


def main():
    os.makedirs(OUT, exist_ok=True)
    for existing in os.listdir(OUT):
        if existing.endswith(".csv"):
            os.remove(os.path.join(OUT, existing))

    buckets = {}
    labels = {}
    for dataset in DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                uid = (row.get("UID") or "").strip()
                if not uid:
                    continue
                for item in (row.get("Other_Names") or "").split(","):
                    parsed = split_item(item)
                    if not parsed:
                        continue
                    label, slug, designation, rest = parsed
                    if dataset == "galaxy_clusters" and slug != "abell":
                        continue
                    labels[slug] = label
                    buckets.setdefault(slug, {})[(designation, uid)] = {
                        "designation": designation,
                        "key": sort_key(rest),
                        "uid": uid,
                        "id": (row.get("ID") or "").strip(),
                        "dataset": dataset,
                        "primary_name": (row.get("Primary_Name") or "").strip(),
                    }

    index = {}
    for slug in sorted(buckets):
        rows = sorted(buckets[slug].values(), key=lambda item: (item["key"], item["designation"], item["uid"]))
        filename = slug + ".csv"
        with open(os.path.join(OUT, filename), "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["Designation", "UID", "ID", "Dataset", "Primary_Name"])
            for item in rows:
                writer.writerow([
                    item["designation"], item["uid"], item["id"],
                    item["dataset"], item["primary_name"],
                ])
        index[slug] = {"label": labels[slug], "file": filename, "rows": len(rows)}

    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    readme = [
        "# By designation",
        "",
        "Index generated from the canonical catalog. One row = one designation → one UID.",
        "Full records stay in the CSV files under `catalog/`; nothing is copied here.",
        "",
        "Coloane: `Designation, UID, ID, Dataset, Primary_Name`.",
        "Sorting: ascending number (every digit group), then UID.",
        "",
    ]
    for slug in sorted(index):
        item = index[slug]
        readme.append(f"- `{item['file']}` — {item['label']} ({item['rows']} entries)")
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(readme) + "\n")

    total = sum(item["rows"] for item in index.values())
    print(f"{len(index)} files, {total} entries")
    for slug in sorted(index):
        item = index[slug]
        print(f"  {item['file']:<20} {item['rows']:>6}")


if __name__ == "__main__":
    main()
