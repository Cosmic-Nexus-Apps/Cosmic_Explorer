#!/usr/bin/env python3
"""Find an object in the catalog by name, with typo tolerance.

Searches Primary_Name, every entry of Other_Names and the UID. Exact match beats
prefix, prefix beats substring, and anything else is scored by similarity, so
"califronia" still finds "California Nebula".

Usage:
  python scripts/find_object.py                    # interactive
  python scripts/find_object.py -q "califronia"
"""
import argparse
import csv
import difflib
import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
DATASETS = ["nebulae", "galaxies", "star_clusters", "galaxy_clusters", "extrema", "stars"]
LIMIT = 8


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load():
    objects = []
    for dataset in DATASETS:
        path = os.path.join(CATALOG, dataset + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                names = [row.get("Primary_Name", "")] + (row.get("Other_Names") or "").split(",")
                candidates = [normalize(name) for name in names if normalize(name) not in ("", "-")]
                objects.append({
                    "uid": row.get("UID", "").strip(),
                    "id": row.get("ID", "").strip(),
                    "dataset": dataset,
                    "name": (row.get("Primary_Name") or "-").strip(),
                    "other": (row.get("Other_Names") or "-").strip(),
                    "magnitude": (row.get("Magnitude") or "").strip(),
                    "distance": (row.get("Distance_ly") or row.get("Distance_Mly") or "").strip(),
                    "distance_unit": "ly" if (row.get("Distance_ly") or "").strip() else "Mly",
                    "ra": (row.get("RA_deg") or "").strip(),
                    "dec": (row.get("DEC_deg") or "").strip(),
                    "candidates": candidates,
                    "uid_key": normalize(row.get("UID", "")),
                })
    return objects


def score(obj, query):
    best = 0.0
    for candidate in obj["candidates"] + [obj["uid_key"]]:
        if candidate == query:
            return 1.0
        if len(query) >= 3 and candidate.startswith(query):
            best = max(best, 0.95)
        elif query in candidate:
            best = max(best, 0.9)
        else:
            best = max(best, difflib.SequenceMatcher(None, query, candidate).ratio())
    return best


def search(objects, query):
    clean = normalize(query)
    if len(clean) < 2:
        return []
    scored = [(score(obj, clean), obj) for obj in objects]
    scored = [item for item in scored if item[0] >= 0.6]
    scored.sort(key=lambda item: (-item[0], item[1]["uid"]))
    return scored[:LIMIT]


def show(results):
    if not results:
        print("  Nothing found.")
        return
    for ratio, obj in results:
        print()
        # Numele obiectului; daca potrivirea e aproximativa, o aratam discret.
        mark = "" if ratio >= 0.9 else f"   (~{ratio:.2f})"
        print(f"  {obj['name']}{mark}")
        print(f"    {obj['uid']} · {obj['dataset']} · {obj['id']}")
        if obj["other"] not in ("", "-"):
            print(f"    {obj['other']}")
        facts = []
        if obj["magnitude"] not in ("", "0", "0.0"):
            facts.append(f"mag {obj['magnitude']}")
        if obj["distance"] not in ("", "0", "0.0"):
            facts.append(f"dist {obj['distance']} {obj['distance_unit']}")
        if obj["ra"]:
            facts.append(f"RA {obj['ra']}")
        if obj["dec"]:
            facts.append(f"DEC {obj['dec']}")
        if facts:
            print("    " + " · ".join(facts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--query")
    args = parser.parse_args()

    objects = load()
    print(f"{len(objects)} objects loaded.")
    if args.query:
        show(search(objects, args.query))
        return

    while True:
        try:
            query = input("\nName (Enter = exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query or query == "0":
            break
        show(search(objects, query))


if __name__ == "__main__":
    main()
