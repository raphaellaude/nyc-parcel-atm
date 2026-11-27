---
type: Dataset
title: NYC MapPLUTO history (2002–2026)
description: Every NYC tax lot from 25 annual MapPLUTO releases (2002–2026) in a normalized schema. Single-year FlatGeobufs and combined hive-partitioned GeoParquets.
resource: https://data.parcels.nyc/pluto/
tags: [nyc, parcels, tax-lots, pluto, land-use, zoning, geospatial, time-series]
sources:
  - resource: https://www.nyc.gov/content/planning/pages/resources/datasets/mappluto-pluto-change
    title: NYC Department of City Planning — MapPLUTO archive
  - resource: https://s-media.nyc.gov/agencies/dcp/assets/files/pdf/data-tools/bytes/pluto_readme.pdf
    title: PLUTO data dictionary
  - resource: https://github.com/raphaellaude/nyc-parcel-atm
    title: GitHub repo containing ELT including schema normalization
generated:
  by: claude-code/claude-opus-5-5
  at: 2026-11-27
verified:
  by: human:raphaellaude
  at: 2026-11-27
status: stable
---

# Overview

MapPLUTO is NYC's tax lot dataset: one polygon per lot, with about 100 attributes covering land use, zoning, buildings, ownership and assessed value. This dataset combines 25 annual releases, from 2002 to 2026. That is about 850,000 lots per year and 21.4M rows in total. Column names have been harmonized across years. The data is public, read-only, and served over HTTPS. It needs no credentials, and HTTP range requests are supported.

# Layout

```
https://data.parcels.nyc/pluto/
├── pluto.duckdb                                   # DuckDB database with a `pluto` view over all Parquet files
├── fgb/
│   ├── pluto02.fgb                                # one FlatGeobuf per release year, 02 … 26
│   ├── …
│   └── pluto26.fgb
└── parquet/
    ├── borough=BK/cd=301/data.parquet             # one file per borough × community district, all years
    ├── …
    └── borough=SI/cd=595/data.parquet
```

| | FlatGeobuf (`fgb/`) | GeoParquet (`parquet/`) |
|---|---|---|
| Granularity | One file per year (`pluto{YY}.fgb`, YY = `02`…`26`), about 700MB each | 91 files; each holds every year for one `borough` × `cd` |
| CRS | **EPSG:4326** (longitude, latitude) | **EPSG:4326 / OGC:CRS84** (longitude, latitude) |
| Ordering | Packed Hilbert R-tree spatial index | Rows sorted by Hilbert curve, then `year`; 16,384-row row groups |
| Columns | That year's harmonized columns, as published | Union of all years' columns, plus `year`, `bbl`, `bbox` |
| Best for | Point and small-area lookups for one year | Longitudinal, multi-year, aggregate and attribute queries |

## Which format to use

- **Point lookups (what lot is at this location in year X?)**: use the **FGB** for that year. DuckDB pushes the `ST_Intersects` filter down to the FGB spatial index, so only the index pages and matching features are fetched, not the whole 700MB file. A lookup takes a few seconds.
- **Longitudinal analysis (how did this lot or area change?) and aggregates**: use the **Parquet**. Filter in this order:
  1. `borough` and `cd`. These are hive partitions, so other files are skipped entirely.
  2. `bbox.xmin/xmax/ymin/ymax`. Row-group statistics skip non-overlapping row groups, which works well because rows are Hilbert ordered.
  3. Any other columns, such as `bbl` or `year`.
- If you don't know a location's `cd`, either do one FGB point lookup first (it returns `borough` and `cd`), or filter the Parquet by `bbox` alone. That costs one footer read per file, 91 in total.

## Partitions

- `borough`: `MN` (Manhattan), `BX` (Bronx), `BK` (Brooklyn), `QN` (Queens), `SI` (Staten Island).
- `cd`: a three-digit community district. The first digit is the borough (1 = MN, 2 = BX, 3 = BK, 4 = QN, 5 = SI). For example, `105` is Manhattan CD 5 (Midtown).
  - Joint interest areas such as parks and airports have codes 164, 226–228, 355–356, 480–484 and 595.
  - `cd=0` holds lots with no community district.
  - A few lots carry a `cd` from another borough (for example `borough=BX/cd=401`). These come from the source data.
- Run `SELECT DISTINCT borough, cd FROM parcels.pluto ORDER BY ALL` for the exact list.

# Schema

The Parquet has 130 columns. The ones most often used:

| Column | Type | Notes |
|---|---|---|
| `year` | INTEGER | Release year, 2002–2026 (Parquet only; for FGBs, it's the file name) |
| `bbl` | BIGINT | Borough-block-lot ID, `borocode * 1e9 + block * 1e4 + lot`. Recomputed for every year in the Parquet, so it is a stable key across years. In the FGBs it is a DOUBLE and missing for 2002–2004. |
| `borough`, `cd` | VARCHAR, BIGINT | Partition keys (see above) |
| `borocode`, `block`, `lot` | numeric | Components of the BBL |
| `address` | VARCHAR | Street address |
| `ownername` | VARCHAR | Owner of record |
| `landuse` | VARCHAR | Land use category code, `01`–`11` |
| `bldgclass` | VARCHAR | Building class (e.g. `O4` office tower, `D4` elevator co-op) |
| `zonedist1`…`zonedist4`, `overlay1`, `overlay2`, `spdist1`… | VARCHAR | Zoning districts, overlays, special districts |
| `yearbuilt`, `yearalter1`, `yearalter2` | numeric | Year built and altered |
| `numbldgs`, `numfloors` | numeric | Buildings on the lot; floors in the tallest building |
| `unitsres`, `unitstotal` | numeric | Residential units; total units |
| `lotarea`, `bldgarea`, `resarea`, `comarea`, `officearea`, `retailarea`, … | numeric | Areas in square feet |
| `builtfar`, `residfar`, `commfar`, `facilfar` | DOUBLE | Built and maximum allowed floor area ratios |
| `assessland`, `assesstot`, `exempttot` | DOUBLE | Assessed land value, total value, exempt value (USD) |
| `histdist`, `landmark` | VARCHAR | Historic district, landmark name |
| `geom` | GEOMETRY | Lot polygon in lon/lat (EPSG:4326) in both formats |
| `bbox` | STRUCT(xmin, ymin, xmax, ymax) | Bounding box of `geom` in lon/lat, for row-group pruning (Parquet only) |

For full column definitions, see the PLUTO data dictionary linked in `sources`. See GitHub repo linked in `sources` for schema normalization including dropped / renamed columns from original source.

## Caveats

- **Columns vary by year.** DCP has added, renamed and dropped fields over time. A column that doesn't exist in a year is NULL for that year's Parquet rows, and absent from that year's FGB.
  - Examples: `council` is missing in 2002; `bct2020` exists only from 2022; `latitude`/`longitude` exist only from 2020.
  - Check coverage with `SELECT year, count(colname) FROM parcels.pluto GROUP BY ALL`.
- **Types are widened in the Parquet.** Numeric columns whose type drifted across releases are DOUBLE. `zipcode`, `schooldist` and similar codes are VARCHAR. Cast as needed.
- **2002**: the community district was published as `cd2`. It is mapped to `cd` in the Parquet; the FGB keeps `cd2`.
- Lots are re-drawn and re-numbered over time, through mergers, apportionments and condo conversions. A location's `bbl` may change between years, so for "what was here" questions use a spatial filter rather than `bbl`.
- Only lots with geometry are included.

# Examples

All examples are DuckDB SQL and require **DuckDB ≥ 2.0**. The FGB examples rely on 2.0's automatic spatial filter pushdown into `ST_Read`. In prior versions of DuckDB, `ST_Read` requires an explicit `spatial_filter` or `spatial_filter_box` for spatial predicate pushdown.

## Setup

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

-- Optional: attach the catalog once to get the `parcels.pluto` view over all Parquet files.
ATTACH 'https://data.parcels.nyc/pluto/pluto.duckdb' AS parcels (READ_ONLY);
```

## Point lookup for one year (FGB)

What lot contains the Empire State Building (lon -73.9857, lat 40.7484) in 2026? `ST_Point` takes longitude first. The `/vsicurl/` prefix makes GDAL use efficient HTTP range reads.

```sql
SELECT address, ownername, bbl, borough, cd, yearbuilt, numfloors, bldgclass, assesstot
FROM ST_Read('/vsicurl/https://data.parcels.nyc/pluto/fgb/pluto26.fgb')
WHERE ST_Intersects(geom, ST_Point(-73.9857, 40.7484));
```

Lots within a bounding box (here, the few blocks around the same point, about 120 lots):

```sql
SELECT bbl, address, landuse, numfloors
FROM ST_Read('/vsicurl/https://data.parcels.nyc/pluto/fgb/pluto26.fgb')
WHERE ST_Intersects(geom, ST_MakeEnvelope(-73.9877, 40.7469, -73.9837, 40.7499));
```

## History of one lot (Parquet)

```sql
SELECT year, ownername, bldgclass, numfloors, assesstot
FROM parcels.pluto
WHERE borough = 'MN' AND cd = 105 AND bbl = 1008350041
ORDER BY year;
```

## History of a location across all years (Parquet)

The `bbox` predicates prune row groups, and `ST_Intersects` gives the exact answer. Add `borough`/`cd` if known to skip other files.

```sql
SELECT year, bbl, address, ownername, landuse, unitsres, assesstot
FROM parcels.pluto
WHERE bbox.xmin <= -73.9857 AND bbox.xmax >= -73.9857
  AND bbox.ymin <= 40.7484  AND bbox.ymax >= 40.7484
  AND ST_Intersects(geom, ST_Point(-73.9857, 40.7484))
ORDER BY year;
```

## Aggregates over time (Parquet)

Residential units by borough for selected years. Only the needed columns are fetched, but a citywide query like this one reads from all files, so expect it to take up to a minute over the network. Filter by `borough`/`cd` wherever possible.

```sql
SELECT year, borough, sum(unitsres)::BIGINT AS residential_units
FROM parcels.pluto
WHERE year IN (2002, 2014, 2026)
GROUP BY ALL
ORDER BY ALL;
```

Lots built since 2010 in Brooklyn CD 1 (Williamsburg/Greenpoint), as of 2026:

```sql
SELECT count(*) AS lots, sum(unitsres)::BIGINT AS residential_units
FROM parcels.pluto
WHERE borough = 'BK' AND cd = 301 AND year = 2026 AND yearbuilt >= 2010;
```

## Reading one partition without the catalog

Each Parquet file can be read directly by URL. HTTPS URLs can't be globbed, so list the files explicitly or use `parcels.pluto`.

```sql
SELECT year, count(*) AS lots
FROM read_parquet('https://data.parcels.nyc/pluto/parquet/borough=MN/cd=105/data.parquet')
GROUP BY ALL
ORDER BY year;
```

## Exporting for other tools

DuckDB 2.0 needs `geometry_always_xy` set before a GDAL export, so that lon/lat is written in the right axis order.

```sql
SET geometry_always_xy = true;

COPY (
    SELECT bbl, year, landuse, assesstot, geom
    FROM parcels.pluto
    WHERE borough = 'MN' AND cd = 105 AND year = 2026
) TO 'midtown_2026.geojson' WITH (FORMAT GDAL, DRIVER 'GeoJSON');
```
