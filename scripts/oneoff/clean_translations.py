#!/usr/bin/env python3
"""Keep only real translations: a language cell identical to the English name is blanked.

The app falls back to the English name when a translation is missing, so removing
"Sirius" from the Romanian column changes nothing on screen but stops pretending
there is a translation.

Usage:
  python scripts/clean_translations.py
  python scripts/clean_translations.py --apply
"""
import argparse
import csv
import glob
import os
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATIONS = os.path.join(ROOT, "catalog", "translations")

LANGUAGES = ["Name_RO", "Name_DE", "Name_FR", "Name_ES", "Name_IT", "Name_PT", "Name_PL", "Name_NL"]


def key(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    total_cleared = 0
    for path in sorted(glob.glob(os.path.join(TRANSLATIONS, "*.csv"))):
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames
            rows = list(reader)

        cleared = 0
        kept = 0
        for row in rows:
            english = row.get("Name_EN", "")
            if not key(english):
                continue
            for language in LANGUAGES:
                if language not in row:
                    continue
                value = row.get(language, "")
                if not str(value).strip():
                    continue
                if key(value) == key(english):
                    row[language] = ""
                    cleared += 1
                else:
                    kept += 1

        print(f"{os.path.basename(path):36} identice șterse: {cleared:5} | traduceri reale: {kept:5}")
        total_cleared += cleared

        if not args.apply:
            continue
        # Un rând fără nicio traducere nu aduce nimic: aplicația cade oricum pe numele englez.
        kept_rows = [row for row in rows if any(str(row.get(language) or "").strip() for language in LANGUAGES)]
        dropped = len(rows) - len(kept_rows)
        if dropped:
            print(f"    rânduri fără nicio traducere, scoase: {dropped}")
        if cleared or dropped:
            newline = "\r\n" if open(path, "rb").read(4096).count(b"\r\n") else "\n"
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=header, lineterminator=newline)
                writer.writeheader()
                writer.writerows(kept_rows)

    print(f"\nTOTAL celule identice golite: {total_cleared}")
    print("APPLIED" if args.apply else "DRY-RUN (nothing written)")


if __name__ == "__main__":
    main()
