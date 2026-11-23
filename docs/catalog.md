# The catalog

Six CSV files with celestial objects, built for astrophotography planning. They are the **source of truth**: every application receives a copy generated from them, never the other way round.

**Current version: v2** · 57,380 objects · CC BY-SA 4.0.

| File | Objects | Content |
|---|---:|---|
| `catalog/nebulae.csv` | 2,646 | emission, reflection, planetary, dark nebulae and supernova remnants |
| `catalog/galaxies.csv` | 9,918 | galaxies of every morphological type |
| `catalog/star_clusters.csv` | 3,181 | open and globular clusters |
| `catalog/galaxy_clusters.csv` | 53 | galaxy groups and clusters |
| `catalog/stars.csv` | 41,529 | stars to magnitude 8 |
| `catalog/extrema.csv` | 53 | black holes, quasars, pulsars, deep fields |

Every object carries multiple catalog designations - 53 families in total
(Messier, NGC, IC, Caldwell, Sharpless, Barnard, LDN, LBN, Collinder, Melotte, Abell, Arp,
PGC, UGC, UGCA, MCG, ESO, MWSC, HIP, HD, HR, SAO, Gliese and more).
The full list with row counts is in `catalog/by-designation/index.json`.

---

## 1. Columns

### Shared

| Column | Type | What it is |
|---|---|---|
| `ID` | text | position in the catalog (`CE-N-1`, `CE-SC-4-O`). Renumbered on every sort. |
| `UID` | text | the object's identity (`N1`, `G3`, `SC4`). Never changed, never moved, never reused. |
| `Primary_Name` | text | proper name (`Horsehead Nebula`). `-` when there is none. |
| `Other_Names` | list | catalog designations, ordered: M, NGC, IC, C, Sh2, B, LDN, LBN, Mel, Cr, PGC, UGC, ESO, MWSC, SAO, HD, HIP. |
| `RA_deg`, `DEC_deg` | number | J2000 coordinates, decimal degrees. |
| `Constellation` | text | IAU constellation, full name (`Orion`). |
| `Magnitude` | number | apparent magnitude; `0` means unknown. |
| `Size_W_arcmin`, `Size_H_arcmin` | number | major and minor axis, arcminutes. |
| `Distance_ly` or `Distance_Mly` | number | light years (Milky Way objects) or million light years (galaxies). |
| `Recommendation_Level` | number | how suitable the object is **for astrophotography**: `0` low, `1` notable, `2` recommended. |
| `Position_Angle_deg` | number | orientation on the sky, `0–360`; `0` means unknown. |
| `Surface_Brightness` | number | magnitude per square arcsecond. |
| `Type`, `Nebula_Type`, `Extrema_Type` | text | object class. |
| `Opacity` | number | opacity of dark nebulae, `1-5`. |

### Per file

| File | Own columns |
|---|---|
| `nebulae.csv` | `Nebula_Type`, `Opacity`, `Distance_ly`, `Related_Star` |
| `galaxies.csv` | `Type`, `Surface_Brightness`, `Distance_Mly`, `Neighbor_Star` |
| `star_clusters.csv` | `Type`, `Distance_ly`, `Neighbor_Star` |
| `galaxy_clusters.csv` | `Type`, `Distance_Mly` |
| `stars.csv` | `Type` (spectral: `A0`, `K2`, `M3e`), `Distance_ly` |
| `extrema.csv` | `Extrema_Type`, `Surface_Brightness`, `Distance_ly` |

### Cross-references

Two dataset-specific columns point at a different object. They are **not aliases** and
never appear in `Other_Names`, the search, or `by-designation/`:

| Column | File | What it is |
|---|---|---|
| `Related_Star` | `nebulae.csv` | the star that lights the nebula (`HD 192163 / HIP 99546`). 14 nebulae have one. |
| `Neighbor_Star` | `galaxies.csv`, `star_clusters.csv` | a bright star close enough to matter for framing (`TYC 3017-939-1`). 64 galaxies and 1 cluster have one. |

`validate_catalog.py` rejects star or galaxy designations left in `Other_Names` for these datasets.

### `Type` values

| File | Values |
|---|---|
| `nebulae.csv` | `DARK_NEBULA`, `EMISSION_NEBULA`, `PLANETARY_NEBULA`, `SUPERNOVA_REMNANT`, `NEBULA` |
| `galaxies.csv` | `SPIRAL_GALAXY`, `LENTICULAR_GALAXY`, `ELLIPTICAL_GALAXY`, `IRREGULAR_GALAXY`, `GALAXY` |
| `star_clusters.csv` | `OPEN_CLUSTER`, `GLOBULAR_CLUSTER` |
| `galaxy_clusters.csv` | `GALAXY_GROUP`, `GALAXY_CLUSTER` |
| `extrema.csv` | `BLACK_HOLE`, `QUASAR`, `PULSAR`, `NEUTRON_STAR`, `EXOPLANET`, `STAR_RECORD`, `DEEP_FIELD` |

---

## 2. Conventions

- **UTF-8**: names with non-ASCII characters (M87* (Pōwehi)) read correctly.
- **Comma separator**: columns are separated by `,`.
- **Quotes**: a field is quoted only when it would otherwise break the row, meaning it contains a comma. `M 31, NGC 224` is written `"M 31, NGC 224"`; `Sirius` is written plain.
- **`0` means unknown**, not a real value. Applies to magnitude, distance, size and angle.
- **`-` means absent**: no proper name, or an empty name list.
- Decimal numbers use a dot, no thousands separator.

---

## 3. Row order

| File | Sorted by | Ties broken by |
|---|---|---|
| nebulae, galaxies, star_clusters, galaxy_clusters | area, descending (W × H) | magnitude asc, constellation, RA, DEC |
| stars | magnitude, ascending | RA, DEC |
| extrema | **unsorted** — a list of records, not a sky catalog | — |

Dark nebulae (`DARK_NEBULA`) sort by opacity instead of magnitude: they have no magnitude of their own.

Re-sort with `scripts/sort_catalog.py --order area --renumber --apply` (stars: `--order magnitude --renumber --only stars`). `ID` is renumbered; `UID` stays.

---

## 4. ID and UID

| | `UID` | `ID` |
|---|---|---|
| What it is | identity | position in the catalog |
| Example | `G3` | `CE-G-3` |
| Changes? | **never** | yes, on every sort |
| Reused? | **never** | yes |
| Used for | saving: journal, favourites, plans, links | display, order, lookup |

> **Save the UID. Show the ID.**

If you save an ID you saved a position: after the next sort it points at another object. If you save a UID, the object is always found.

---

## 5. Duplicates and aliases

When two rows described the same object, one was merged away. Its UID is never reused; it goes into:

- `catalog/uid-aliases.json` — `{ "N2042": "N1758" }`
- `catalog/uid-registry.json` — `"retired": { "N2042": { "merged_into": "N1758" } }`

Applications resolve the alias on read, so an old reference still finds the surviving object. The registry is the complete ledger of UIDs, used by the validator to catch deletions and reuses.

What was merged and why: `history.md`.

---

## 6. Point sources

`extrema.csv` holds black holes, quasars and pulsars — objects with no apparent extent. Because of that:

- `Size_W_arcmin` and `Size_H_arcmin` are `0` (except seven objects that do have a surrounding region);
- `Surface_Brightness` is `0` for all of them: brightness per square arcsecond is meaningless for a point;
- `Distance_ly` exists only where it can be derived (11 of 53, quasars with redshift).

The columns stay in the file so the schema is identical across all catalogs.

---

## 7. Sources and licences

| Source | What it added | Licence |
|---|---|---|
| HYG Database v4.1 | stars: HIP, HD, HR, Gliese, Bayer, names, magnitude, distance, spectral type | CC BY-SA 4.0 |
| OpenNGC | galaxies, nebulae, clusters: designations, sizes, magnitudes, SB, angle | CC BY-SA 4.0 |
| Stellarium DSO 3.23 | Sh2, LDN, LBN, Cr, Mel, B, C, PGC, UGC; missing declinations | GPL-2.0+ |
| MWSC (Kharchenko 2013) | distances for star clusters | CDS/VizieR data |

Raw files used (SHA256, first 16 characters):

| File | SHA256 |
|---|---|
| `hygdata_v41.csv` | `D9F69FD86BBF90A4` |
| `opengc_ngc.csv` | `54ABEA0B57B0A103` |
| `opengc_addendum.csv` | `C93F983DDA6780B7` |
| `stellarium_nebulae_catalog.txt` | `38A7C8C19B07BB3B` |
| `mwsc.tsv` | VizieR `J/A+A/558/A53`, 3,007 rows |

Full attribution: `catalog/ATTRIBUTION.md`. Derived data is distributed under **CC BY-SA 4.0** (`LICENSE`).

---

## 8. What is missing, and why

| Field | Coverage | Reason |
|---|---|---|
| Nebula distance | 2% | none of the sources publish nebula distances; NED has them but is unreachable from the working network |
| Galaxy distance | 28% | OpenNGC has no distance column; the values are historical |
| Nebula magnitude | 13% | dark nebulae (`LDN`) have no magnitude of their own |
| Cluster magnitude | 24% | MWSC does not publish magnitudes |
| Abell designations | 8 of 12 galaxy clusters | the other four are regions, not Abell clusters; the 41 galaxy groups carry HCG numbers instead |

Stars have 100% distance (HYG carries parallax) and 100% magnitude.

### Star identifiers

`Other_Names` order for stars: **HIP → HD → HR → SAO → TYC → Gaia DR3 → 2MASS → Gliese → Bayer/Flamsteed**.
The current catalog carries HIP, HD, HR, SAO, Gliese and Bayer/Flamsteed; TYC, Gaia and 2MASS would need extra downloads.
