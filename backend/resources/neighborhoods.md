---
type: Dataset
title: NYC neighborhoods and community districts
description: Lookup table mapping NYC neighborhood names (2020 NTAs) to boroughs and community districts, with NTA boundaries. Use it to turn a neighborhood name into the `borough`/`cd` partitions and polygon for PLUTO queries.
resource: https://data.parcels.nyc/neighborhoods/
tags: [nyc, neighborhoods, nta, community-districts, boroughs, geospatial, lookup]
sources:
  - resource: https://data.cityofnewyork.us/City-Government/2020-Neighborhood-Tabulation-Areas-NTAs-/9nt8-h7nd
    title: NYC Open Data — 2020 Neighborhood Tabulation Areas (NTAs)
  - resource: https://data.cityofnewyork.us/City-Government/Community-Districts/5crt-au7u
    title: NYC Open Data — Community Districts
  - resource: https://github.com/raphaellaude/nyc-parcel-atm
    title: GitHub repo containing the ELT that builds this table
generated:
  by: claude-code/claude-opus-5-5
  at: 2026-11-27
verified:
  by: human:raphaellaude
  at: 2026-11-27
status: draft
---

# Overview

NYC has no official neighborhood boundaries. The closest thing is the Department of City Planning's 2020 **Neighborhood Tabulation Areas (NTAs)**: 262 named areas such as `Greenpoint` or `Bedford-Stuyvesant (West)`. Each NTA belongs to one borough. It can cross **community district (CD)** lines, so the relationship between NTAs and CDs is many-to-many.

This dataset is one denormalized table with **one row per NTA × CD pair**. About 436 rows cover all 262 NTAs and 71 CDs (59 community districts plus 12 joint interest areas such as parks and airports). Each row carries borough, CD and NTA attributes, the share of the NTA that falls in that CD, and the NTA's polygon.

Use it with the `pluto` dataset (call `read_resource` with id `pluto`) to answer questions about a neighborhood, such as "how has land use changed in Greenpoint?" Look the name up here to get `borough`, `cd` and `geom`. Then query PLUTO, filtered by those partitions and spatially by the NTA polygon.

# Layout

```
https://data.parcels.nyc/
├── pluto/pluto.duckdb                    # also exposes this table as the `neighborhoods` view
└── neighborhoods/
    └── neighborhoods.parquet             # GeoParquet, ~1.4MB, EPSG:4326 (lon, lat)
```

The file is small enough to read whole. Either `ATTACH` the PLUTO catalog and use `parcels.neighborhoods`, or `read_parquet` the URL directly.

# Schema

| Column | Type | Notes |
|---|---|---|
| `borough` | VARCHAR | `MN`, `BX`, `BK`, `QN`, `SI`. Same codes as the PLUTO `borough` partition. |
| `boroname` | VARCHAR | `Manhattan`, `Bronx`, `Brooklyn`, `Queens`, `Staten Island` |
| `borocode` | INTEGER | 1 = MN, 2 = BX, 3 = BK, 4 = QN, 5 = SI |
| `cd` | INTEGER | Three-digit community district, such as `301`. Same as the PLUTO `cd` partition. |
| `cd_name` | VARCHAR | DCP's descriptive name for the CD, such as `Williamsburg-Greenpoint` |
| `cd_type` | VARCHAR | `community district`, or `joint interest area` (codes 164, 226–228, 355–356, 480–484, 595) |
| `nta2020` | VARCHAR | NTA code, such as `BK0101`. Unique per NTA, repeated once per CD it touches. |
| `ntaname` | VARCHAR | NTA name, such as `Greenpoint` |
| `ntaabbrev` | VARCHAR | Short NTA label, such as `Grnpt` |
| `ntatype` | VARCHAR | `residential`, `park`, `cemetery`, `airport`, `special use` (Navy Yard, Sunnyside Yards, etc.) or `rikers island` |
| `cdta2020`, `cdtaname` | VARCHAR | The NTA's Community District Tabulation Area, DCP's NTA-based approximation of a CD, such as `BK01` / `BK01 Williamsburg-Greenpoint (CD 1 Equivalent)` |
| `nta_area_pct` | DOUBLE | Fraction of the NTA's area inside this CD's boundary, 0–1 |
| `lots` | BIGINT | Number of 2026 PLUTO lots inside the NTA whose `cd` is this CD |
| `nta_lots_pct` | DOUBLE | `lots` as a fraction of all the NTA's 2026 lots, 0–1 |
| `geom` | GEOMETRY | **NTA** polygon in lon/lat (EPSG:4326). Repeated on every row for the NTA. |
| `bbox` | STRUCT(xmin, ymin, xmax, ymax) | Bounding box of `geom`, for pruning PLUTO row groups |

## How rows are chosen

A pair is included if the NTA overlaps the CD's boundary by at least 1% of its area, **or** if any 2026 PLUTO lot inside the NTA has that `cd`. PLUTO's lot-level `cd` doesn't always match the CD polygons. The second rule makes sure that every PLUTO partition holding an NTA's lots is listed.

Reading the shares:

- The row with the highest `nta_lots_pct` is the NTA's **primary CD**. Use it to answer "what community district is X in?"
- Rows with a tiny `nta_lots_pct` (a handful of lots, `nta_area_pct` ≈ 0) are mostly geocoding strays in PLUTO. Include them when choosing partitions to scan, since an extra partition costs little. Don't report them as real relationships.
- To find a CD's neighborhoods, filter by `cd`. Order by `nta_lots_pct` to rank NTAs mostly inside the CD above those that only clip it.

# Finding a neighborhood by name

NTA names are DCP's, not always the colloquial ones. Many NTAs combine several neighborhoods (`Downtown Brooklyn-DUMBO-Boerum Hill`). Large neighborhoods are split by direction (`Bedford-Stuyvesant (East)`, `Bedford-Stuyvesant (West)`), and names use full spellings (`Bedford-Stuyvesant`, not `Bed-Stuy`).

1. Search `ntaname` and `cd_name` case-insensitively with `ILIKE '%term%'`. `cd_name` catches district-level names such as `Williamsburg-Greenpoint`.
2. If nothing matches, expand abbreviations and nicknames yourself (Bed-Stuy → Bedford-Stuyvesant, LIC → Long Island City, UES → Upper East Side). You can also rank by `jaro_winkler_similarity(lower(ntaname), lower('term'))`.
3. If several NTAs match (for example `Williamsburg`, `South Williamsburg`, `East Williamsburg`), decide whether the user means one NTA or their union, and say which you used.
4. For a point (an address or landmark with known coordinates), find its NTA with `ST_Contains(geom, ST_Point(lon, lat))`.

# Caveats

- **The boundaries are 2020 vintage.** They are applied to every PLUTO year. NTA and CD lines are geographic, so this is fine for "what was here" questions over 2002–2026. The `lots` counts reflect 2026 lots only.
- **Lot-level CDs drift over time.** Older PLUTO releases sometimes assigned lots to other CDs. Filtering PLUTO by the `cd` values listed here, plus the NTA polygon, may miss a very small number of historical lots. For exact completeness, drop the `cd` filter and keep only the `bbox` and polygon filters. That reads one footer from each of PLUTO's 91 files.
- **Assign lots by a point, not by overlap.** Lots on an NTA boundary intersect two NTAs. Test `ST_Within(ST_PointOnSurface(lot.geom), nta.geom)` so that each lot is counted once.
- **Join on `borough` and `cd` as well as the geometry.** An NTA's polygon repeats on each of its CD rows. A purely spatial join to a multi-CD NTA would count each lot once per row. Otherwise, select `DISTINCT nta2020, geom` first.
- Joint interest areas have their own `cd` codes, such as `164` for Central Park, in both this table and PLUTO.

# Examples

All examples are DuckDB SQL and require **DuckDB ≥ 2.0**.

## Setup

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

ATTACH 'https://data.parcels.nyc/pluto/pluto.duckdb' AS parcels (READ_ONLY);
-- or, without the catalog:
-- CREATE VIEW neighborhoods AS SELECT * FROM read_parquet('https://data.parcels.nyc/neighborhoods/neighborhoods.parquet');
```

## Look up a neighborhood

```sql
SELECT nta2020, ntaname, borough, cd, cd_name, nta_lots_pct
FROM parcels.neighborhoods
WHERE ntaname ILIKE '%greenpoint%' OR cd_name ILIKE '%greenpoint%'
ORDER BY nta2020, nta_lots_pct DESC;
```

This returns `Greenpoint` (BK0101) entirely in `BK` / `301`, along with the other NTAs in CD 301 (`Williamsburg-Greenpoint`). An NTA that crosses a line, such as `Clinton Hill`, returns one row per CD (`302` at 96.5% of lots, `303` at 3.5%).

## Neighborhood history from PLUTO

"How has land use changed in Greenpoint?" Join PLUTO to the NTA's rows on `borough` and `cd`, then filter spatially by the NTA polygon. DuckDB pushes the join keys down to PLUTO's hive partitions as dynamic filters, so only the NTA's partitions are read. Here that is one file, and the query takes a few seconds over the network. Joining on `borough`/`cd` also means each lot matches exactly one row of a multi-CD NTA.

```sql
SELECT p.year, p.landuse, count(*) AS lots, sum(p.lotarea)::BIGINT AS lot_area
FROM parcels.pluto AS p
JOIN parcels.neighborhoods AS n
  ON p.borough = n.borough AND p.cd = n.cd
 AND p.bbox.xmin <= n.bbox.xmax AND p.bbox.xmax >= n.bbox.xmin
 AND p.bbox.ymin <= n.bbox.ymax AND p.bbox.ymax >= n.bbox.ymin
 AND ST_Within(ST_PointOnSurface(p.geom), n.geom)
WHERE n.ntaname = 'Greenpoint'
  AND p.year IN (2002, 2014, 2026)
GROUP BY ALL
ORDER BY ALL;
```

For a whole community district, skip this table and filter PLUTO by `borough` and `cd` alone.

## Neighborhoods in a community district

```sql
SELECT ntaname, ntatype, nta_lots_pct, nta_area_pct
FROM parcels.neighborhoods
WHERE cd = 301
ORDER BY nta_lots_pct DESC;
```

## Which neighborhood is a point in?

```sql
SELECT DISTINCT nta2020, ntaname, boroname
FROM parcels.neighborhoods
WHERE ST_Contains(geom, ST_Point(-73.9545, 40.7290));
```

## Compare neighborhoods

Residential units in 2026 for every NTA in Brooklyn CD 1, with each lot assigned to exactly one NTA:

```sql
SELECT n.ntaname, sum(p.unitsres)::BIGINT AS residential_units
FROM parcels.pluto AS p
JOIN parcels.neighborhoods AS n
  ON p.borough = n.borough AND p.cd = n.cd
 AND ST_Within(ST_PointOnSurface(p.geom), n.geom)
WHERE n.cd = 301 AND p.year = 2026
GROUP BY ALL
ORDER BY residential_units DESC;
```
