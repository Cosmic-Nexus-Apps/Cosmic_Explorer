#!/usr/bin/env python3
"""Enrich the Cosmic Explorer catalog from HYG v4.1 and OpenNGC.

Dry-run by default. Never changes UID or ID.
Only fills missing/zero fields and adds catalog identifiers to Other_Names.

Usage:
  python scripts/import_sources.py            # dry-run
  python scripts/import_sources.py --apply
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

STAR_ORDER = ["HIP", "HD", "HR", "SAO", "TYC", "Gaia", "2MASS", "Gl", "BF"]
DEEP_ORDER = [
    "M", "NGC", "IC", "C", "Sh2", "B", "LDN", "LBN", "Abell", "Arp",
    "Mel", "Cr", "PGC", "UGC", "ESO", "MWSC", "SAO", "HD", "HIP",
]

DESIGNATION = re.compile(
    r"^(M|NGC|IC|C|Sh2|B|LDN|LBN|Abell|Arp|Mel|Cr|PGC|UGC|ESO|MWSC|SAO|HD|HIP|HR|Gl|Gaia|2MASS)\s*[- ]?(\d+[A-Z]?)$",
    re.IGNORECASE,
)


def read_csv(path, delimiter=","):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


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


def normalize_designation(value):
    text = str(value or "").strip()
    match = DESIGNATION.match(text)
    if not match:
        return None
    catalog = match.group(1)
    canonical = {
        "m": "M", "ngc": "NGC", "ic": "IC", "c": "C", "sh2": "Sh2",
        "b": "B", "ldn": "LDN", "lbn": "LBN", "abell": "Abell", "arp": "Arp",
        "mel": "Mel", "cr": "Cr", "pgc": "PGC", "ugc": "UGC", "eso": "ESO",
        "mwsc": "MWSC", "sao": "SAO", "hd": "HD", "hip": "HIP", "hr": "HR",
        "gl": "Gl", "gaia": "Gaia", "2mass": "2MASS",
    }[catalog.lower()]
    number_text = match.group(2)
    if number_text[-1].isalpha():
        number_text = f"{int(number_text[:-1])}{number_text[-1]}"
    else:
        number_text = str(int(number_text))
    return canonical, number_text


def parse_names(text):
    groups = {}
    unknown = []
    for raw in str(text or "").split(","):
        item = raw.strip()
        if not item or item == "-":
            continue
        parsed = normalize_designation(item)
        if parsed:
            catalog, value = parsed
            groups.setdefault(catalog, set()).add(value)
        else:
            unknown.append(item)
    return groups, unknown


def format_names(groups, unknown, order):
    parts = []
    for catalog in order:
        values = groups.get(catalog, set())
        if not values:
            continue
        if catalog == "BF":
            parts.extend(sorted(values))
        else:
            parts.extend(
                f"{catalog} {value}"
                for value in sorted(values, key=lambda item: (int(re.match(r"\d+", item).group()), item))
            )
    parts.extend(unknown)
    return ", ".join(dict.fromkeys(parts)) if parts else "-"


def add_names(text, additions):
    groups, unknown = parse_names(text)
    for catalog, value in additions:
        groups.setdefault(catalog, set()).add(str(value))
    return groups, unknown


def write_rows(path, header, rows):
    with open(path, "rb") as fh:
        newline = "\r\n" if b"\r\n" in fh.read(4096) else "\n"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator=newline)
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(name, "") for name in header])


def load_hyg():
    path = os.path.join(SOURCE, "hygdata_v41.csv")
    if not os.path.exists(path):
        raise SystemExit("Missing source_data/hygdata_v41.csv")
    rows = read_csv(path)
    grid = {}
    for row in rows:
        ra_hours, dec = number(row.get("ra")), number(row.get("dec"))
        if ra_hours is None or dec is None:
            continue
        ra = ra_hours * 15.0
        grid.setdefault((math.floor(ra / 0.1), math.floor(dec / 0.1)), []).append(row)
    return grid


def load_openngc():
    paths = [os.path.join(SOURCE, "opengc_ngc.csv"), os.path.join(SOURCE, "opengc_addendum.csv")]
    rows = []
    for path in paths:
        if os.path.exists(path):
            rows.extend(read_csv(path, delimiter=";"))
    by_m, by_ngc, by_ic = {}, {}, {}
    for row in rows:
        if row.get("M"):
            by_m[str(int(row["M"]))] = row
        name = str(row.get("Name", "")).strip().upper()
        match = re.match(r"^(NGC|IC)(\d+)([A-Z]?)$", name)
        if match:
            key = f"{int(match.group(2))}{match.group(3)}"
            (by_ngc if match.group(1) == "NGC" else by_ic)[key] = row
    return by_m, by_ngc, by_ic


STELLARIUM_COLUMNS = {
    "NGC": 16, "IC": 17, "M": 18, "C": 19, "B": 20,
    "Sh2": 21, "LDN": 24, "LBN": 25, "Cr": 26, "Mel": 27,
    "PGC": 28, "UGC": 29,
}


def stal_number(value):
    """Stellarium foloseste 99 ca 'necunoscut' si 0 ca 'lipsa'."""
    result = number(value)
    if result is None or result == 0 or result >= 99:
        return None
    return result


def norm_number(text):
    text = str(text).strip().upper()
    if text[-1:].isalpha():
        return f"{int(text[:-1])}{text[-1]}"
    return str(int(text))


def load_stellarium():
    path = os.path.join(SOURCE, "stellarium_nebulae_catalog.txt")
    if not os.path.exists(path):
        return {}
    index = {catalog: {} for catalog in STELLARIUM_COLUMNS}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) < 37:
                continue
            for catalog, column in STELLARIUM_COLUMNS.items():
                cell = cells[column].strip()
                if cell and cell != "0":
                    index[catalog].setdefault(norm_number(cell), cells)
    return index


def load_mwsc():
    path = os.path.join(SOURCE, "mwsc.tsv")
    if not os.path.exists(path):
        return {}
    table = {}
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cells = line.rstrip("\n").split("\t")
            if len(cells) < 7 or not cells[0].strip().isdigit():
                continue
            parsecs = number(cells[6])
            ra, dec = number(cells[3]), number(cells[4])
            if parsecs and ra is not None and dec is not None:
                table[cells[0].strip().lstrip("0") or "0"] = (ra, dec, parsecs)
    return table


def angular_separation_arcmin(ra1, dec1, ra2, dec2):
    d1, d2 = math.radians(dec1), math.radians(dec2)
    dra = math.radians(ra1 - ra2)
    h = math.sin((d2 - d1) / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(dra / 2) ** 2
    return math.degrees(2 * math.asin(math.sqrt(h))) * 60.0


def fill_mwsc_distances(rows, table, apply_changes):
    stats = {"matched": 0, "distance": 0, "wrong_centre": 0}
    for row in rows:
        if number(row.get("Distance_ly")):
            continue
        ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
        if ra is None or dec is None:
            continue
        groups, _ = parse_names(row.get("Other_Names"))
        for value in sorted_ids(groups, "MWSC"):
            entry = table.get(value)
            if entry is None:
                continue
            if angular_separation_arcmin(ra, dec, entry[0], entry[1]) > 60:
                # Numarul MWSC din catalog nu e al acestui obiect; nu imprumutam distanta.
                stats["wrong_centre"] += 1
                continue
            stats["matched"] += 1
            stats["distance"] += 1
            if apply_changes:
                row["Distance_ly"] = f"{entry[2] * 3.26156:.0f}"
            break
    return stats


def enrich_stars(rows, grid, apply_changes):
    stats = {"matched": 0, "names": 0, "identifiers": 0, "magnitude": 0, "distance": 0, "type": 0, "unmatched": 0}
    samples = []
    for row in rows:
        ra, dec = number(row.get("RA_deg")), number(row.get("DEC_deg"))
        if ra is None or dec is None:
            stats["unmatched"] += 1
            continue
        cx, cy = math.floor(ra / 0.1), math.floor(dec / 0.1)
        best, bestd = None, 1e9
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for candidate in grid.get((cx + dx, cy + dy), []):
                    cra, cdec = number(candidate.get("ra")) * 15.0, number(candidate.get("dec"))
                    if cra is None or cdec is None:
                        continue
                    distance = (cra - ra) ** 2 + (cdec - dec) ** 2
                    if distance < bestd:
                        bestd, best = distance, candidate
        # 2 arcsec: at 3 arcmin the match hit another star and the name landed on the wrong object.
        if best is None or bestd > (2.0 / 3600.0) ** 2:
            stats["unmatched"] += 1
            continue
        stats["matched"] += 1
        additions = []
        for catalog, column in (("HIP", "hip"), ("HD", "hd"), ("HR", "hr")):
            value = str(best.get(column, "")).strip()
            if value:
                additions.append((catalog, value))
        gl = str(best.get("gl", "")).strip()
        if gl:
            additions.append(("Gl", gl.replace("Gl ", "").replace("GJ ", "")))
        bf = str(best.get("bf", "")).strip()
        if bf:
            additions.append(("BF", bf))
        if additions:
            groups, unknown = add_names(row.get("Other_Names"), additions)
            new_names = format_names(groups, unknown, STAR_ORDER)
            if new_names != row.get("Other_Names"):
                stats["identifiers"] += 1
                if apply_changes:
                    row["Other_Names"] = new_names
        if row.get("Primary_Name", "").strip() in ("", "-") and best.get("proper"):
            stats["names"] += 1
            if apply_changes:
                row["Primary_Name"] = best["proper"].strip()
        if not number(row.get("Magnitude")) and number(best.get("mag")) is not None:
            stats["magnitude"] += 1
            if apply_changes:
                row["Magnitude"] = str(best["mag"])
        if not number(row.get("Distance_ly")) and number(best.get("dist")):
            stats["distance"] += 1
            if apply_changes:
                row["Distance_ly"] = f"{float(best['dist']) * 3.26156:.3f}"
        if not row.get("Type", "").strip() and best.get("spect"):
            stats["type"] += 1
            if apply_changes:
                row["Type"] = best["spect"].strip()
        if len(samples) < 5:
            samples.append((row.get("UID"), row.get("Primary_Name"), row.get("Other_Names")))
    return stats, samples


def sorted_ids(groups, catalog):
    """Ordine deterministica; seturile de stringuri nu sunt stabile intre procese."""
    return sorted(groups.get(catalog, set()), key=lambda value: (int(re.match(r"\d+", value).group()), value))


def openngc_match(groups, by_m, by_ngc, by_ic):
    row = None
    for value in sorted_ids(groups, "M"):
        if value in by_m:
            row = by_m[value]
            break
    if row is None:
        for value in sorted_ids(groups, "NGC"):
            if value in by_ngc:
                row = by_ngc[value]
                break
    if row is None:
        for value in sorted_ids(groups, "IC"):
            if value in by_ic:
                row = by_ic[value]
                break
    if row is None:
        return None
    ids = []
    if row.get("M"):
        ids.append(("M", str(int(row["M"]))))
    name = str(row.get("Name", "")).strip().upper()
    found = re.match(r"^(NGC|IC)(\d+)([A-Z]?)$", name)
    if found:
        ids.append((found.group(1), f"{int(found.group(2))}{found.group(3)}"))
    return dict(row, _ids=ids)


def stellarium_match(groups, index):
    if not index:
        return None
    for catalog in ("M", "NGC", "IC", "Sh2", "LDN", "LBN", "B", "Cr", "Mel", "PGC", "UGC"):
        for value in sorted_ids(groups, catalog):
            row = index[catalog].get(value)
            if row is None:
                continue
            ids = []
            for other, column in STELLARIUM_COLUMNS.items():
                cell = row[column].strip()
                if cell and cell != "0" and other == catalog:
                    # Doar desemnarea pe care s-a facut potrivirea. Restul
                    # codurilor din randul Stellarium pot descrie alt obiect.
                    ids.append((other, norm_number(cell)))
            # Dark nebulae have no magnitude of their own; the source value belongs to a field star.
            has_magnitude = row[5].strip() not in ("", "DN", "BN")
            return {
                "Common names": "",
                "MajAx": stal_number(row[7]),
                "MinAx": stal_number(row[8]),
                "B-Mag": stal_number(row[3]) if has_magnitude else None,
                "V-Mag": stal_number(row[4]) if has_magnitude else None,
                "SurfBr": None,
                "PosAng": stal_number(row[9]),
                "_ids": ids,
            }
    return None


def enrich_deep(rows, matchers, apply_changes):
    stats = {"matched": 0, "names": 0, "identifiers": 0, "size": 0, "magnitude": 0, "surface": 0, "angle": 0, "unmatched": 0}
    samples = []
    for row in rows:
        groups, unknown = parse_names(row.get("Other_Names"))
        match = None
        for matcher in matchers:
            match = matcher(groups)
            if match:
                break
        if match is None:
            stats["unmatched"] += 1
            continue
        stats["matched"] += 1
        additions = match.get("_ids") or []
        if additions:
            groups, unknown = add_names(row.get("Other_Names"), additions)
            new_names = format_names(groups, unknown, DEEP_ORDER)
            if new_names != row.get("Other_Names"):
                stats["identifiers"] += 1
                if apply_changes:
                    row["Other_Names"] = new_names
        common = str(match.get("Common names", "")).strip()
        if row.get("Primary_Name", "").strip() in ("", "-") and common:
            first = common.split(",")[0].strip()
            if first and not normalize_designation(first):
                stats["names"] += 1
                if apply_changes:
                    row["Primary_Name"] = first
        def fill(column, source_column):
            if number(row.get(column)) is None or number(row.get(column)) == 0:
                value = number(match.get(source_column))
                if value is not None and value != 0:
                    return value
            return None
        for column, source_column, key in (
            ("Size_W_arcmin", "MajAx", "size"),
            ("Size_H_arcmin", "MinAx", "size"),
        ):
            value = fill(column, source_column)
            if value is not None:
                stats[key] += 1
                if apply_changes:
                    row[column] = f"{value:g}"
        if not number(row.get("Size_H_arcmin")) and number(row.get("Size_W_arcmin")):
            if apply_changes:
                row["Size_H_arcmin"] = row["Size_W_arcmin"]
        magnitude = fill("Magnitude", "V-Mag") or fill("Magnitude", "B-Mag")
        if magnitude is not None:
            stats["magnitude"] += 1
            if apply_changes:
                row["Magnitude"] = f"{magnitude:g}"
        surface = fill("Surface_Brightness", "SurfBr")
        if surface is not None:
            stats["surface"] += 1
            if apply_changes:
                row["Surface_Brightness"] = f"{surface:g}"
        angle = fill("Position_Angle_deg", "PosAng")
        if angle is not None and 0 < angle <= 360:
            stats["angle"] += 1
            if apply_changes:
                row["Position_Angle_deg"] = f"{angle:g}"
        if len(samples) < 5:
            samples.append((row.get("UID"), row.get("Primary_Name"), row.get("Other_Names")))
    return stats, samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    grid = load_hyg()
    by_m, by_ngc, by_ic = load_openngc()
    index = load_stellarium()
    mwsc = load_mwsc()
    matchers = [
        lambda groups: openngc_match(groups, by_m, by_ngc, by_ic),
        lambda groups: stellarium_match(groups, index),
    ]

    stars_path = os.path.join(CATALOG, "stars.csv")
    with open(stars_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        stars = list(reader)
    star_stats, star_samples = enrich_stars(stars, grid, args.apply)
    if args.apply:
        write_rows(stars_path, header, stars)
    print("stars:", star_stats)
    for sample in star_samples:
        print("  ", sample)

    for filename in ("nebulae.csv", "galaxies.csv", "star_clusters.csv"):
        path = os.path.join(CATALOG, filename)
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            rows = list(reader)
        stats, samples = enrich_deep(rows, matchers, args.apply)
        if filename == "star_clusters.csv":
            stats["mwsc_distance"] = fill_mwsc_distances(rows, mwsc, args.apply)["distance"]
        if args.apply:
            write_rows(path, header, rows)
        print(filename + ":", stats)
        for sample in samples:
            print("  ", sample)

    print("APPLY" if args.apply else "DRY-RUN (nothing written)")


if __name__ == "__main__":
    main()
