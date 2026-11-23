#!/usr/bin/env python3
"""Add the missing stars from HYG, up to a magnitude limit.

Existing rows are never touched, and the new ones are appended after the last
UID so the ID order stays ascending. A designation (HIP/HD/HR...) is only used if
no other object already carries it.

Usage:
  python scripts/add_stars.py                     # dry-run, limita 8.0
  python scripts/add_stars.py --limit 7.5
  python scripts/add_stars.py --apply
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
SOURCE = os.path.join(ROOT, "source_data")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from import_sources import STAR_ORDER, format_names, number, parse_names, read_csv, write_rows  # noqa: E402

MATCH_ARCSEC = 10.0
POSITION_TOLERANCE = (MATCH_ARCSEC / 3600.0) ** 2


def build_grid(rows):
    grid = {}
    for row in rows:
        ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
        if ra is None or dec is None:
            continue
        grid.setdefault((math.floor(ra / 0.1), math.floor(dec / 0.1)), []).append((ra, dec))
    return grid


def already_present(grid, ra, dec):
    cx, cy = math.floor(ra / 0.1), math.floor(dec / 0.1)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for cra, cdec in grid.get((cx + dx, cy + dy), []):
                if (cra - ra) ** 2 + (cdec - dec) ** 2 <= POSITION_TOLERANCE:
                    return True
    return False


def nearest_hyg(grid, ra, dec):
    cx, cy = math.floor(ra / 0.1), math.floor(dec / 0.1)
    best, bestd = None, 1e9
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for entry in grid.get((cx + dx, cy + dy), []):
                distance = (entry[0] - ra) ** 2 + (entry[1] - dec) ** 2
                if distance < bestd:
                    bestd, best = distance, entry[2]
    return best if best is not None and bestd <= POSITION_TOLERANCE else None


def clean_spectral(value):
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    text = re.sub(r"(Ia|Ib|I{1,3}|IV|V)$", "", text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=float, default=8.0)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    path = os.path.join(CATALOG, "stars.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        stars = list(reader)

    hyg = read_csv(os.path.join(SOURCE, "hygdata_v41.csv"))
    hyg_rows = []
    for row in hyg:
        ra_hours, dec = number(row.get("ra")), number(row.get("dec"))
        if ra_hours is None or dec is None:
            continue
        hyg_rows.append((ra_hours * 15.0, dec, row))

    grid = build_grid(stars)
    hyg_grid = {}
    for ra, dec, row in hyg_rows:
        hyg_grid.setdefault((math.floor(ra / 0.1), math.floor(dec / 0.1)), []).append((ra, dec, row))

    # Abreviere HYG -> nume complet, invatata din stelele deja potrivite.
    names = {}
    for star in stars:
        ra, dec = number(star.get("RA_deg")), number(star.get("DEC_deg"))
        if ra is None or dec is None:
            continue
        match = nearest_hyg(hyg_grid, ra, dec)
        if not match:
            continue
        abbreviation = (match.get("con") or "").strip()
        constellation = (star.get("Constellation") or "").strip()
        if abbreviation and constellation:
            names.setdefault(abbreviation, constellation)
    print(f"constellations learned: {len(names)}")

    # Garda: nicio desemnare folosita deja nu se repeta.
    used = set()
    names_in_use = set()
    for dataset in ("stars", "nebulae", "galaxies", "star_clusters"):
        for row in read_csv(os.path.join(CATALOG, dataset + ".csv")):
            for item in (row.get("Other_Names") or "").split(","):
                value = re.sub(r"[^a-z0-9]+", "", item.lower())
                if value:
                    used.add(value)
            proper = re.sub(r"[^a-z0-9]+", "", (row.get("Primary_Name") or "").lower())
            if proper and proper != "-":
                names_in_use.add(proper)

    last = max(int(re.sub(r"\D", "", row["ID"])) for row in stars)
    fresh = []
    for ra, dec, row in hyg_rows:
        if (row.get("proper") or "").strip() == "Sol":
            continue  # The Sun is not a catalog star; it has its own section.
        magnitude = number(row.get("mag"))
        if magnitude is None or magnitude > args.limit:
            continue
        if already_present(grid, ra, dec):
            continue
        # The star already exists under a slightly different position: same HIP/HD.
        hip = str(row.get("hip", "")).strip()
        hd = str(row.get("hd", "")).strip()
        if hip and f"hip{hip}" in used:
            continue
        if not hip and hd and f"hd{hd}" in used:
            continue
        fresh.append((magnitude, ra, dec, row))
    fresh.sort(key=lambda item: (item[0], item[2], item[1]))
    print(f"new stars up to mag {args.limit}: {len(fresh)}")

    new_rows = []
    skipped_names = 0
    for magnitude, ra, dec, row in fresh:
        groups = {}
        for catalog, column in (("HIP", "hip"), ("HD", "hd"), ("HR", "hr")):
            value = str(row.get(column, "")).strip()
            if not value:
                continue
            key = re.sub(r"[^a-z0-9]+", "", f"{catalog}{value}".lower())
            if key in used:
                skipped_names += 1
                continue
            used.add(key)
            groups.setdefault(catalog, set()).add(value)
        gliese = str(row.get("gl", "")).strip()
        if gliese:
            value = gliese.replace("Gl ", "").replace("GJ ", "")
            key = re.sub(r"[^a-z0-9]+", "", f"Gl{value}".lower())
            if key not in used:
                used.add(key)
                groups.setdefault("Gl", set()).add(value)
        bayer = str(row.get("bf", "")).strip()
        if bayer:
            groups.setdefault("BF", set()).add(bayer)

        last += 1
        distance = number(row.get("dist"))
        proper = (row.get("proper") or "").strip()
        proper_key = re.sub(r"[^a-z0-9]+", "", proper.lower())
        if proper and proper_key in names_in_use:
            proper = "-"  # the name already belongs to another object in the catalog
        elif proper:
            names_in_use.add(proper_key)
        new_rows.append({
            "ID": f"CE-S-{last}",
            "Primary_Name": proper or "-",
            "Other_Names": format_names(groups, [], STAR_ORDER),
            "RA_deg": f"{ra:.5f}",
            "DEC_deg": f"{dec:.5f}",
            "Magnitude": f"{magnitude:g}",
            "UID": f"S{last}",
            "Distance_ly": f"{distance * 3.26156:.3f}" if distance else "0",
            "Type": clean_spectral(row.get("spect")),
            "Recommendation_Level": "0",
            "Constellation": names.get((row.get("con") or "").strip(), (row.get("con") or "").strip()),
        })

    print(f"designations skipped (already used): {skipped_names}")
    print(f"new UID range: S{last - len(new_rows) + 1} .. S{last}")
    for sample in new_rows[:3] + new_rows[-2:]:
        print("  ", sample["ID"], "|", sample["Primary_Name"], "|", sample["Other_Names"], "| mag", sample["Magnitude"], "|", sample["Constellation"])

    if not args.apply:
        print("\nDRY-RUN (nothing written)")
        return

    write_rows(path, header, stars + new_rows)
    print(f"\nAPPLIED: {len(new_rows)} stars added, total {len(stars) + len(new_rows)}")


if __name__ == "__main__":
    main()
