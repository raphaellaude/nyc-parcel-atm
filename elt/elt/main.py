import os
import json
import logging
import subprocess
from pandas import DataFrame
from pathlib import Path
from typing import Union
from itertools import chain

from .assets import download_zipfiles, unzip_zipfiles, get_pluto_key
from .database import create_table, column_availibility, column_similarity, with_conn
from .constants import ASSETS_DIR, YEARS
from .jinja import render_template
from .frontend import create_json


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        create_table(alias, shp_files)  # pyright: ignore


def harmonize_pluto_columns() -> DataFrame:
    """
    Harmonize PLUTO columns across years.
    """
    tables = [get_pluto_key(year, "shp") for year in YEARS]
    col_availibility = column_availibility(tables)  # pyright: ignore
    match_df = column_similarity(col_availibility)

    print(
        "Column matches with >80 similarity, which don't exist in the same year's data: "
    )
    print(match_df)

    return match_df


@with_conn
def rename_columns(conn) -> None:
    """
    Rename columns in the database based on harmonized columns.
    """
    # do it three times just to make sure that linked renamings converge on a single name
    for _ in range(3):
        for year in YEARS:
            alias = get_pluto_key(year, "shp")
            to_rename_sql = render_template("columns_to_rename.jinja", table=alias)
            cursor = conn.execute(to_rename_sql)
            to_rename = cursor.fetchall()

            rename_sql = render_template(
                "rename_columns.jinja", table=alias, rename_columns=to_rename
            )
            conn.execute(rename_sql)

            print(f"Renamed columns for {alias}.")

    conn.query(
        """
ALTER TABLE pluto02_shp RENAME yearalter TO yearalter1;
ALTER TABLE pluto02_shp RENAME far TO builtfar;
ALTER TABLE pluto03_shp RENAME far TO builtfar;
        """
    )


@with_conn
def export_fgbs(conn, years: list[int] | None = None):
    """
    Export Feature Geometries Binary (FGB) files for each year's PLUTO data.
    """
    out_path = os.path.join(ASSETS_DIR, "fgbs")
    if not os.path.exists(out_path):
        os.makedirs(out_path, exist_ok=True)

    _years = years or YEARS

    for year in _years:
        logger.info(f"Exporting FGB for year {year}")
        alias = get_pluto_key(year, "shp")
        out_table_id = f"pluto{str(year).zfill(2)}"
        fgb_sql = render_template(
            "export_fgb.jinja",
            table=alias,
            out_path=out_path,
            out_table_id=out_table_id,
        )
        conn.execute(fgb_sql)


@with_conn
def export_for_tiling(conn, years: list[int] | None = None):
    """
    Export layer for tippecannoe tiling for each year's PLUTO data.
    """
    out_path = os.path.join(ASSETS_DIR, "tiling-inputs")
    if not os.path.exists(out_path):
        print(f"Creating {out_path}. Does not exist.")
        os.makedirs(out_path, exist_ok=True)

    _years = years or YEARS

    for year in _years:
        print(f"Exporting layer for tippecanoe tiling for year {year}")
        alias = get_pluto_key(year, "shp")
        fgb_sql = render_template(
            "export_for_tiling.jinja", table=alias, out_path=out_path
        )
        conn.execute(fgb_sql)

        out_file = os.path.join(out_path, alias + ".fgb")
        dest_file = os.path.join(out_path, alias + "_wgs.fgb")

        subprocess.run(["ogr2ogr", "-t_srs", "EPSG:4326", dest_file, out_file])

        os.remove(out_file)


def create_tilesets(years: list[int] | None = None):
    fbg_tippecanoe_path = os.path.join(ASSETS_DIR, "tiling-inputs")
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
    to_include_params = [f"--include={col}" for col in to_include]

    cast_to_int = [
        "landuse",
        "unitsres",
        "yearalter1",
        "yearbuilt",
    ]
    cast_to_int_params = list(
        chain.from_iterable([("-T", f"{col}:int") for col in cast_to_int])
    )

    _years = years or YEARS

    for year in _years:
        print(f"Creating tileset for {year}")
        alias = get_pluto_key(year, "shp_wgs")
        in_file = os.path.join(fbg_tippecanoe_path, f"{alias}.fgb")
        out_file = os.path.join(out_path, f"{alias}.pmtiles")
        command = [
            "tippecanoe",
            "-z",
            "13",
            "-o",
            out_file,
            "--coalesce-smallest-as-needed",
            "--extend-zooms-if-still-dropping",
            "--calculate-feature-index",
            *to_include_params,
            *cast_to_int_params,
            "--force",
            "-l",
            alias,
            in_file,
        ]
        print(f"Running with command:\n{command}")
        subprocess.run(command, check=True)


def get_tileset_json(out_path: Union[str, Path]):
    data = create_json()

    with open(out_path, "w") as f:
        f.write(json.dumps(data))
