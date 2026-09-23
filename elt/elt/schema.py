"""
Canonical schema for the normalized PLUTO parquet exports.

The "core" dataset contains the columns that exist (after harmonization) in every
PLUTO year, cast to a single type so all years can be queried together. Keep this
in sync with `mcp/internal/catalog/catalog.go`, which documents these columns for
the parcel data MCP server.
"""

# Column name -> DuckDB type. Order here is the column order in the export.
CORE_COLUMNS: dict[str, str] = {
    "borocode": "SMALLINT",
    "borough": "VARCHAR",
    "block": "INTEGER",
    "lot": "INTEGER",
    "address": "VARCHAR",
    "zipcode": "INTEGER",
    "ownername": "VARCHAR",
    "ownertype": "VARCHAR",
    "landuse": "SMALLINT",
    "bldgclass": "VARCHAR",
    "zonedist1": "VARCHAR",
    "zonedist2": "VARCHAR",
    "overlay1": "VARCHAR",
    "overlay2": "VARCHAR",
    "spdist1": "VARCHAR",
    "spdist2": "VARCHAR",
    "splitzone": "VARCHAR",
    "histdist": "VARCHAR",
    "landmark": "VARCHAR",
    "lotarea": "DOUBLE",
    "lotfront": "DOUBLE",
    "lotdepth": "DOUBLE",
    "irrlotcode": "VARCHAR",
    "bldgfront": "DOUBLE",
    "bldgdepth": "DOUBLE",
    "numbldgs": "INTEGER",
    "numfloors": "DOUBLE",
    "unitsres": "INTEGER",
    "unitstotal": "INTEGER",
    "comarea": "DOUBLE",
    "resarea": "DOUBLE",
    "builtfar": "DOUBLE",
    "yearbuilt": "SMALLINT",
    "yearalter1": "SMALLINT",
    "yearalter2": "SMALLINT",
    "assessland": "DOUBLE",
    "assesstot": "DOUBLE",
    "exempttot": "DOUBLE",
    "areasource": "VARCHAR",
    "schooldist": "SMALLINT",
    "policeprct": "SMALLINT",
    "firecomp": "VARCHAR",
    "xcoord": "DOUBLE",
    "ycoord": "DOUBLE",
}

# Source geometries are NY State Plane Long Island (US feet).
SOURCE_CRS = "EPSG:2263"
# Parquet exports are reprojected to WGS84 (lon/lat axis order).
EXPORT_CRS = "EPSG:4326"
