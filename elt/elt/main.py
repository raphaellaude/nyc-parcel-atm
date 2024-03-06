import os
import glob
import duckdb
import subprocess
from pandas import DataFrame
from pathlib import Path

from .assets import download_zipfiles, unzip_zipfiles, get_pluto_key
from .database import create_table, column_availibility, column_similarity, CONN
from .constants import ASSETS_DIR, YEARS
from .jinja import render_template


def download_and_unzip() -> None:
    """
    Download, unzip, and load PLUTO data into duckdb database.
    """
    zip_files = download_zipfiles()
    print(zip_files)
    unzip_zipfiles(ASSETS_DIR)


def populate_duckdb_database() -> None:
    """
    Populate duckdb database with PLUTO data.
    """
    for year in YEARS:
        alias = get_pluto_key(year, "shp")
        shp_dir = Path(os.path.join(ASSETS_DIR, alias))
        print(f"Shp dir: {shp_dir}")
        shp_files = list(shp_dir.glob("**/*mappluto.shp", case_sensitive=False))
        print(f"Found {len(shp_files)} shapefiles for {alias}.")
        create_table(alias, shp_files)


def harmonize_pluto_columns() -> DataFrame:
    """
    Harmonize PLUTO columns across years.
    """
    tables = [get_pluto_key(year, "shp") for year in YEARS]
    col_availibility = column_availibility(tables)
    match_df = column_similarity(col_availibility)

    print(
        "Column matches with >80 similarity, which don't exist in the same year's data: "
    )
    print(match_df)

    return match_df


def rename_columns() -> None:
    """
    Rename columns in the database based on harmonized columns.
    """
    # do it three times just to make sure that linked renamings converge on a single name
    for _ in range(3):
        for year in YEARS:
            alias = get_pluto_key(year, "shp")
            to_rename_sql = render_template("columns_to_rename.jinja", table=alias)
            cursor = CONN.execute(to_rename_sql)
            to_rename = cursor.fetchall()

            rename_sql = render_template(
                "rename_columns.jinja", table=alias, rename_columns=to_rename
            )
            CONN.execute(rename_sql)

            print(f"Renamed columns for {alias}.")

    CONN.query(
        """
ALTER TABLE pluto02_shp RENAME yearalter TO yearalter1;
ALTER TABLE pluto02_shp RENAME far TO builtfar;
ALTER TABLE pluto03_shp RENAME far TO builtfar;
        """
    )


def export_fgbs():
    out_path = os.path.join(ASSETS_DIR, "fgbs")
    if not os.path.exists(out_path):
        os.makedirs(out_path, exist_ok=True)

    for year in YEARS:
        alias = get_pluto_key(year, "shp")
        fgb_sql = render_template("export_fgb.jinja", table=alias, out_path=out_path)
        CONN.execute(fgb_sql)


def export_geojsons_for_tippecannoe():
    out_path = os.path.join(ASSETS_DIR, "geojsons")
    if not os.path.exists(out_path):
        print(f"Creating {out_path}. Does not exist.")
        os.makedirs(out_path, exist_ok=True)

    for year in YEARS:
        print(f"Exporting geojson for tippecanoe for year {year}")
        alias = get_pluto_key(year, "shp")
        fgb_sql = render_template(
            "export_geojson_tippecannoe.jinja", table=alias, out_path=out_path
        )
        CONN.execute(fgb_sql)

        out_file = os.path.join(out_path, alias + ".geojson")
        dest_file = os.path.join(out_path, alias + "_wgs.geojson")

        subprocess.run(["ogr2ogr", "-t_srs", "EPSG:4326", dest_file, out_file])

        os.remove(out_file)


def create_tilesets():
    fbg_tippecanoe_path = os.path.join(ASSETS_DIR, "geojsons")
    out_path = os.path.join(ASSETS_DIR, "tilesets")
    if not os.path.exists(out_path):
        os.makedirs(out_path, exist_ok=True)

    to_include = [
        "landuse",
        "zonedist1",
        "assessland",
        "assesstot",
        "numfloors",
        "yearbuilt",
        "unitsres",
        "bldgclass",
        "yearalter1",
        "builtfar",
    ]

    includes = [f"--include={col}" for col in to_include]

    for year in YEARS:
        print(f"Creating tileset for {year}")
        alias = get_pluto_key(year, "shp_wgs")
        in_file = os.path.join(fbg_tippecanoe_path, f"{alias}.geojson")
        out_file = os.path.join(out_path, f"{alias}.pmtiles")
        subprocess.run(
            [
                "tippecanoe",
                "-z",
                "13",
                "-o",
                out_file,
                "--coalesce-smallest-as-needed",
                "--extend-zooms-if-still-dropping",
                *includes,
                "--force",
                "-l",
                alias,
                in_file,
            ]
        )
