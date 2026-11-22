# History — v1 vs v2

Comparison: **v1** (`source_data/pristine`) vs **v2** (`catalog/`). Regenerate with `python scripts/catalog_audit.py`.

## 1. Objects

| Dataset | v1 | v2 | Difference |
|---|---:|---:|---:|
| nebulae | 2651 | 2646 | -5 |
| galaxies | 9946 | 9918 | -28 |
| star_clusters | 3181 | 3181 | +0 |
| galaxy_clusters | 53 | 53 | +0 |
| stars | 9040 | 41529 | +32489 |
| extrema | 53 | 53 | +0 |
| **Total** | **24924** | **57380** | **+32456** |

## 2. Identifiers and names

| Metric | v1 | v2 |
|---|---:|---:|
| Identifiers in `Other_Names` | 53629 | 153494 |
| Objects with a proper name | 507 | 833 |
| Designations on 2+ objects | 312 | 455 |

"Designations on 2+ objects" = a catalog number that appears on more than one object. It can be correct (M 42 is both a nebula and a cluster) or a mistake. See `catalog.md`.

## 3. Columns, per catalog

### nebulae — 2651 → 2646

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 2651 (100.0%) | 2646 (100.0%) | — |
| `Primary_Name` | 117 (4.4%) | 120 (4.5%) | yes |
| `Other_Names` | 2649 objects · 3048 ID · 1.15/object | 2644 objects · 3595 ID · 1.36/object | yes |
| `RA_deg` | 2649 (99.9%) · min 0.83 · med 270.375 · max 359.75 | 2644 (99.9%) · min 0.83 · med 270.5 · max 359.75 | yes |
| `DEC_deg` | 2466 (93.0%) · min -80.8586 · med 9.7667 · max 88.3333 | 2646 (100.0%) · min -80.8586 · med 8.3333 · max 88.3333 | yes |
| `Size_W_arcmin` | 2648 (99.9%) · min 0.02 · med 11.46 · max 1080 | 2643 (99.9%) · min 0.02 · med 11.54 · max 1080 | yes |
| `Size_H_arcmin` | 2648 (99.9%) · min 0.02 · med 11.3 · max 1080 | 2643 (99.9%) · min 0.02 · med 11.38 · max 1080 | yes |
| `Magnitude` | 241 (9.1%) · min 1 · med 10.9 · max 15.5 | 344 (13.0%) · min 1 · med 10.9 · max 21.5 | yes |
| `UID` | 2651 (100.0%) | 2646 (100.0%) | — |
| `Distance_ly` | 45 (1.7%) · min 410 · med 5000 · max 163000 | 45 (1.7%) · min 410 · med 5000 · max 163000 | — |
| `Nebula_Type` | 2651 (100.0%) · DARK_NEBULA=1979, EMISSION_NEBULA=488, PLANETARY_NEBULA=129, NEBULA=38 | 2646 (100.0%) · DARK_NEBULA=1976, EMISSION_NEBULA=487, PLANETARY_NEBULA=129, NEBULA=37 | yes |
| `Opacity` | 1978 (74.6%) · 4=478, 5=454, 3=418, 2=235 | 1975 (74.6%) · 4=478, 5=453, 3=418, 2=235 | yes |
| `Recommendation_Level` | 149 (5.6%) · 1=90, 2=59 | 149 (5.6%) · 1=90, 2=59 | — |
| `Position_Angle_deg` | 137 (5.2%) · min 3 · med 90 · max 356 | 192 (7.3%) · min 3 · med 90 · max 359 | yes |
| `Constellation` | 2651 (100.0%) | 2646 (100.0%) | — |

### galaxies — 9946 → 9918

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 9946 (100.0%) | 9918 (100.0%) | — |
| `Primary_Name` | 132 (1.3%) | 131 (1.3%) | — |
| `Other_Names` | 9946 objects · 34604 ID · 3.48/object | 9918 objects · 37853 ID · 3.82/object | yes |
| `RA_deg` | 9946 (100.0%) · min 0.0381 · med 185.245 · max 359.961 | 9918 (100.0%) · min 0.0381 · med 185.233 · max 359.961 | yes |
| `DEC_deg` | 9946 (100.0%) · min -89.3345 · med 11.1001 · max 89.0931 | 9918 (100.0%) · min -89.3345 · med 11.167 · max 89.0931 | yes |
| `Size_W_arcmin` | 9942 (100.0%) · min 0.05 · med 1.1 · max 518 | 9918 (100.0%) · min 0.05 · med 1.1 · max 518 | — |
| `Size_H_arcmin` | 9942 (100.0%) · min 0.03 · med 0.63 · max 475 | 9918 (100.0%) · min 0.03 · med 0.62 · max 475 | yes |
| `Magnitude` | 706 (7.1%) · min 0.4 · med 14.995 · max 21.01 | 9703 (97.8%) · min 0.4 · med 14.4 · max 21.01 | yes |
| `Surface_Brightness` | 9506 (95.6%) · min 20.03 · med 23.32 · max 28.48 | 9536 (96.1%) · min 19.93 · med 23.32 · max 28.48 | yes |
| `UID` | 9946 (100.0%) | 9918 (100.0%) | — |
| `Distance_Mly` | 2815 (28.3%) · min 0.163 · med 312.41 · max 55900 | 2814 (28.4%) · min 0.163 · med 312.525 · max 55900 | yes |
| `Type` | 9946 (100.0%) · SPIRAL_GALAXY=5239, LENTICULAR_GALAXY=2479, ELLIPTICAL_GALAXY=1417, GALAXY=557 | 9918 (100.0%) · SPIRAL_GALAXY=5239, LENTICULAR_GALAXY=2479, ELLIPTICAL_GALAXY=1417, GALAXY=529 | yes |
| `Recommendation_Level` | 172 (1.7%) · 1=119, 2=53 | 172 (1.7%) · 1=119, 2=53 | — |
| `Position_Angle_deg` | 144 (1.4%) · min 5 · med 102.5 · max 355 | 9570 (96.5%) · min 1 · med 87 · max 355 | yes |
| `Constellation` | 9946 (100.0%) | 9918 (100.0%) | — |

### star_clusters — 3181 → 3181

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 3181 (100.0%) | 3181 (100.0%) | — |
| `Primary_Name` | 85 (2.7%) | 90 (2.8%) | yes |
| `Other_Names` | 3181 objects · 6479 ID · 2.04/object | 3181 objects · 6523 ID · 2.05/object | yes |
| `RA_deg` | 3181 (100.0%) · min 0.067 · med 143.397 · max 359.772 | 3181 (100.0%) · min 0.067 · med 143.397 · max 359.772 | — |
| `DEC_deg` | 3181 (100.0%) · min -83.9991 · med -18.3787 · max 82.22 | 3181 (100.0%) · min -83.9991 · med -18.3787 · max 82.22 | — |
| `Size_W_arcmin` | 3181 (100.0%) · min 0.6 · med 8.4 · max 330 | 3181 (100.0%) · min 0.6 · med 8.4 · max 330 | — |
| `Size_H_arcmin` | 3181 (100.0%) · min 0.55 · med 8.4 · max 330 | 3181 (100.0%) · min 0.55 · med 8.4 · max 330 | — |
| `Magnitude` | 666 (20.9%) · min 0.5 · med 9.615 · max 14.99 | 759 (23.9%) · min 0.5 · med 9.4 · max 15.15 | yes |
| `UID` | 3181 (100.0%) | 3181 (100.0%) | — |
| `Distance_ly` | 19 (0.6%) · min 153 · med 6440 · max 33900 | 2757 (86.7%) · min 153 · med 6918 · max 269193 | yes |
| `Type` | 3181 (100.0%) · OPEN_CLUSTER=2939, GLOBULAR_CLUSTER=242 | 3181 (100.0%) · OPEN_CLUSTER=2939, GLOBULAR_CLUSTER=242 | — |
| `Recommendation_Level` | 71 (2.2%) · 2=55, 1=16 | 71 (2.2%) · 2=55, 1=16 | — |
| `Position_Angle_deg` | 4 (0.1%) · min 25 · med 70 · max 330 | 135 (4.2%) · min 10 · med 90 · max 330 | yes |
| `Constellation` | 3181 (100.0%) | 3181 (100.0%) | — |

### galaxy_clusters — 53 → 53

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 53 (100.0%) | 53 (100.0%) | — |
| `Primary_Name` | 52 (98.1%) | 52 (98.1%) | — |
| `Other_Names` | 53 objects · 328 ID · 6.19/object | 53 objects · 328 ID · 6.19/object | — |
| `RA_deg` | 53 (100.0%) · min 1.71 · med 169.89 · max 354.073 | 53 (100.0%) · min 1.71 · med 169.89 · max 354.073 | — |
| `DEC_deg` | 53 (100.0%) · min -55.4027 · med 12.83 · max 85.73 | 53 (100.0%) · min -55.4027 · med 12.83 · max 85.73 | — |
| `Size_W_arcmin` | 53 (100.0%) · min 1.5 · med 20 · max 700 | 53 (100.0%) · min 1.5 · med 20 · max 700 | — |
| `Size_H_arcmin` | 53 (100.0%) · min 2 · med 20 · max 700 | 53 (100.0%) · min 2 · med 20 · max 700 | — |
| `Magnitude` | 53 (100.0%) · min 6.9 · med 12 · max 14.5 | 53 (100.0%) · min 6.9 · med 12 · max 14.5 | — |
| `UID` | 53 (100.0%) | 53 (100.0%) | — |
| `Distance_Mly` | 53 (100.0%) · min 12 · med 160 · max 500 | 53 (100.0%) · min 12 · med 160 · max 500 | — |
| `Type` | 53 (100.0%) · GALAXY_GROUP=41, GALAXY_CLUSTER=12 | 53 (100.0%) · GALAXY_GROUP=41, GALAXY_CLUSTER=12 | — |
| `Recommendation_Level` | 38 (71.7%) · 1=23, 2=15 | 38 (71.7%) · 1=23, 2=15 | — |
| `Position_Angle_deg` | 28 (52.8%) · min 5 · med 181.5 · max 355 | 28 (52.8%) · min 5 · med 181.5 · max 355 | — |
| `Constellation` | 53 (100.0%) | 53 (100.0%) | — |

### stars — 9040 → 41529

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 9040 (100.0%) | 41529 (100.0%) | — |
| `Primary_Name` | 68 (0.8%) | 387 (0.9%) | yes |
| `Other_Names` | 9040 objects · 9040 ID · 1.00/object | 41529 objects · 105065 ID · 2.53/object | yes |
| `RA_deg` | 9040 (100.0%) · min 0.08003 · med 176.417 · max 359.98 | 41529 (100.0%) · min 0.00502 · med 176.795 · max 359.98 | yes |
| `DEC_deg` | 9040 (100.0%) · min -88.9566 · med -1.60512 · max 89.2641 | 41529 (100.0%) · min -89.7824 · med -0.29911 · max 89.2641 | yes |
| `Magnitude` | 9040 (100.0%) · min -1.6 · med 6 · max 6.5 | 41529 (100.0%) · min -1.6 · med 7.28 · max 8 | yes |
| `UID` | 9040 (100.0%) | 41529 (100.0%) | — |
| `Distance_ly` | 10 (0.1%) · min 4.37 · med 39.8 · max 863 | 41521 (100.0%) · min 4.321 · med 598.451 · max 326156 | yes |
| `Type` | 9040 (100.0%) · K0=1918, A0=891, G5=625, A2=534 | 41506 (99.9%) · K0=6339, A0=3011, G5=2476, K2=2190 | yes |
| `Recommendation_Level` | 874 (9.7%) · 1=806, 2=68 | 874 (2.1%) · 1=806, 2=68 | — |
| `Constellation` | 9040 (100.0%) | 41529 (100.0%) | — |

### extrema — 53 → 53

| Column | v1 | v2 | Changed |
|---|---|---|---|
| `ID` | 53 (100.0%) | 53 (100.0%) | — |
| `Primary_Name` | 53 (100.0%) | 53 (100.0%) | — |
| `Other_Names` | 53 objects · 130 ID · 2.45/object | 53 objects · 130 ID · 2.45/object | — |
| `RA_deg` | 53 (100.0%) · min 4.424 · med 228.481 · max 356.208 | 53 (100.0%) · min 4.424 · med 228.481 · max 356.208 | — |
| `DEC_deg` | 53 (100.0%) · min -73.4 · med -0.346 · max 81.696 | 53 (100.0%) · min -73.4 · med -0.346 · max 81.696 | — |
| `Size_W_arcmin` | 7 (13.2%) · min 0.1 · med 0.2 · max 3 | 7 (13.2%) · min 0.1 · med 0.2 · max 3 | — |
| `Size_H_arcmin` | 7 (13.2%) · min 0.1 · med 0.2 · max 3 | 7 (13.2%) · min 0.1 · med 0.2 · max 3 | — |
| `Magnitude` | 53 (100.0%) · min 4.3 · med 14.2 · max 99 | 44 (83.0%) · min 4.3 · med 13.3 · max 18.8 | yes |
| `Surface_Brightness` | 53 (100.0%) · min 99 · med 99 · max 99 | 0 (0.0%) | yes |
| `Extrema_Type` | 53 (100.0%) · EXOPLANET=12, STAR_RECORD=12, BLACK_HOLE=9, QUASAR=5 | 53 (100.0%) · EXOPLANET=12, STAR_RECORD=12, BLACK_HOLE=9, QUASAR=5 | — |
| `UID` | 53 (100.0%) | 53 (100.0%) | — |
| `Distance_ly` | 11 (20.8%) · min 960 · med 6500 · max 1.82e+10 | 11 (20.8%) · min 960 · med 6500 · max 1.82e+10 | — |
| `Recommendation_Level` | 53 (100.0%) · 2=53 | 53 (100.0%) · 2=53 | — |
| `Constellation` | 53 (100.0%) | 53 (100.0%) | — |


## What was removed and why

| Item | v1 | v2 | Reason |
|---|---|---|---|
| `Is_Verified` | column in every file | **removed** | manual verification, no longer performed |
| 33 duplicate objects | separate rows | **merged** | same object twice; retired UIDs have aliases |
| 28 objects in `galaxies.csv` that were clusters or nebulae | in galaxies | **moved** where they belong | M 47, NGC 4147, NGC 5189 and others |
| 182 nebulae with `DEC = 0` | on the equator | **real declination** | recovered from Stellarium |
| `99` as "unknown" in extrema | `99` | `0` | one convention across the catalog |

## Where to find v1

The `v1` tag of this repository contains exactly the old data: six CSVs and the translations,
24,924 objects. Tag: `v1`.

