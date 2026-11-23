# Scripts and pipeline

Every tool is Python 3, lives in `scripts/`, and accepts `--help`.

## When new data arrives

```bash
python scripts/import_sources.py            # 1. match HYG / OpenNGC / Stellarium / MWSC
python scripts/import_sources.py --apply    #    repeat until the dry run reports 0 changes
python scripts/enrich_round2.py             # 2. designations from OpenNGC, duplicate-guarded
python scripts/validate_catalog.py --update-registry   # 3. validation + registry
python scripts/build_designation_index.py   # 4. regenerate catalog/by-designation/
python scripts/catalog_audit.py --out docs/history.md
python scripts/verify_all.py                # 5. every check, 14/14
```

Order matters: a designation added now may allow a match on the next run, so the import is repeated until nothing changes.

## Tools

| Script | What it does |
|---|---|
| `import_sources.py` | matches HYG, OpenNGC, Stellarium, MWSC; fills only missing fields |
| `enrich_round2.py` | designations from OpenNGC's `Identifiers` column; one designation can never land on two objects |
| `add_stars.py` | adds the missing HYG stars up to a magnitude (`--limit 8`) |
| `validate_catalog.py` | UIDs, duplicates, coordinates, registry; `--update-registry`, `--check-sort` |
| `sort_catalog.py` | sorting and renumbering: `--order area\|magnitude\|id`, `--renumber`, `--only`, `--export` |
| `build_designation_index.py` | generates `catalog/by-designation/` |
| `verify_all.py` | 14 checks: data, registry, aliases, translations, copies |
| `catalog_audit.py` | v1 vs v2 report: summary plus every column |
| `convert_catalog.py` | interactive CSV/JSON export into `exports/` |
| `find_object.py` | name lookup, typo tolerant |
| `translations_audit.py` | checks translations against the catalog names |

## `scripts/oneoff/` — applied once, kept as history

Run during the v1 → v2 transition, not needed again:

| Script | What it fixed |
|---|---|
| `repair_identifiers.py` | 54 designations and 8 names attached to the wrong row |
| `dedupe_catalog.py` | rows describing the same object |
| `resolve_shared_designations.py` | one designation on two objects, resolved by source position |
| `resolve_cross_dataset.py` | 28 objects moved out of `galaxies.csv` into clusters and nebulae |
| `fix_missing_declination.py` | 182 nebulae sitting on the equator |
| `clean_translations.py` | removed translation cells identical to the English name |

## Folders

| Folder | What it is | Published |
|---|---|---|
| `catalog/` | the data: six CSVs, translations, registry, aliases, index | yes |
| `scripts/` | the tools | yes |
| `docs/` | the documentation | yes |
| `assets/` | the README banner | yes |
| `source_data/` | raw downloads plus the v1 snapshot | **no** |
| `exports/` | generated files for download | **no** |

Copies inside the applications are made by hand; `verify_all.py` checks they match.
