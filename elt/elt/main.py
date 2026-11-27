import json
import logging
import os
import shutil
import subprocess
from itertools import chain
from pathlib import Path

import duckdb
from pandas import DataFrame

from .assets import download_lion, download_zipfiles, get_pluto_key, unzip_zipfiles
from .constants import ASSETS_DIR, DATA_URL, STORAGE_PROFILE, STORAGE_URI, YEARS
from .database import column_availibility, column_similarity, create_table, with_conn
from .frontend import create_json
from .jinja import render_template

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
def export_fgbs(conn, years: list[int] | None = None, wgs84: bool = False):
    """
    Export Feature Geometries Binary (FGB) files for each year's PLUTO data.
    """
    out_path = os.path.join(ASSETS_DIR, "fgbs_wgs84" if wgs84 else "fgbs")
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
            wgs84=wgs84,
        )
        conn.execute(fgb_sql)


@with_conn
def export_parquet(conn):
    """
    Export all years of PLUTO as GeoParquet, hive partitioned by borough and
    community district, Hilbert ordered within each file.
    """
    out_path = os.path.join(ASSETS_DIR, "parquet")
    shutil.rmtree(out_path, ignore_errors=True)

    tables = [(2000 + year, get_pluto_key(year, "shp")) for year in YEARS]
    print("Building export table...")
    conn.execute("SET preserve_insertion_order = false")
    conn.execute(render_template("export_parquet.jinja", tables=tables))

    partitions = conn.execute(
        "SELECT DISTINCT borough, cd FROM pluto_export ORDER BY ALL"
    ).fetchall()

    for borough, cd in partitions:
        partition_dir = os.path.join(out_path, f"borough={borough}", f"cd={cd}")
        os.makedirs(partition_dir, exist_ok=True)
        print(f"Writing {partition_dir}")
        conn.execute(
            f"""
            COPY (
                SELECT * EXCLUDE (borough, cd, hilbert)
                FROM pluto_export
                WHERE borough = $1 AND cd = $2
                ORDER BY hilbert, year
            ) TO '{partition_dir}/data.parquet'
            (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 16384)
            """,
            [borough, cd],
        )

    conn.execute("DROP TABLE pluto_export")


def upload():
    """
    Upload FGBs and GeoParquet to object storage, then publish a DuckDB file
    with a `pluto` view over the uploaded parquet files.
    """
    aws = ["aws", "--profile", STORAGE_PROFILE, "s3"]
    parquet_dir = os.path.join(ASSETS_DIR, "parquet")
    for local, remote in [("fgbs_wgs84", "pluto/fgb"), ("parquet", "pluto/parquet")]:
        print(f"Uploading {local} to {STORAGE_URI}/{remote}")
        subprocess.run(
            [
                *aws,
                "sync",
                "--exclude",
                ".*",
                "--exclude",
                "*/.*",
                os.path.join(ASSETS_DIR, local),
                f"{STORAGE_URI}/{remote}",
            ],
            check=True,
        )

    urls = sorted(
        f"{DATA_URL}/pluto/parquet/{path.relative_to(parquet_dir).as_posix()}"
        for path in Path(parquet_dir).glob("borough=*/cd=*/data.parquet")
    )

    db_path = os.path.join(ASSETS_DIR, "pluto.duckdb")
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"Creating {db_path} with a view over {len(urls)} parquet files")
    with duckdb.connect(db_path) as view_conn:
        view_conn.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
        view_conn.execute(
            f"CREATE VIEW pluto AS SELECT * FROM read_parquet({urls}, hive_partitioning = true)"
        )

    subprocess.run(
        [*aws, "cp", db_path, f"{STORAGE_URI}/pluto/pluto.duckdb"], check=True
    )


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

        subprocess.run(
            ["ogr2ogr", "-t_srs", "EPSG:4326", dest_file, out_file], check=True
        )

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


@with_conn
def create_lion_tileset(conn, version: str):
    """
    Export LION streets for labeling and tile them with tippecanoe.
    """
    zip_path = download_lion(version)
    gdb_path = f"/vsizip/{zip_path}/lion/lion.gdb"

    tiling_inputs = os.path.join(ASSETS_DIR, "tiling-inputs")
    tilesets = os.path.join(ASSETS_DIR, "tilesets")
    os.makedirs(tiling_inputs, exist_ok=True)
    os.makedirs(tilesets, exist_ok=True)

    fgb_path = os.path.join(tiling_inputs, f"lion_{version}.fgb")
    if os.path.exists(fgb_path):
        os.remove(fgb_path)

    print(f"Exporting LION {version} streets to {fgb_path}")
    conn.execute(
        render_template(
            "export_lion_for_tiling.jinja", gdb_path=gdb_path, out_path=fgb_path
        )
    )

    out_file = os.path.join(tilesets, "lion_streets.pmtiles")
    command = [
        "tippecanoe",
        "-Z",
        "11",
        "-z",
        "14",
        "-o",
        out_file,
        "-l",
        "roads",
        "--include=name",
        "--include=kind",
        "--include=min_zoom",
        "-T",
        "min_zoom:int",
        "--no-feature-limit",
        "--no-tile-size-limit",
        "--force",
        fgb_path,
    ]
    print(f"Running with command:\n{command}")
    subprocess.run(command, check=True)


def get_tileset_json(out_path: str | Path):
    data = create_json()

    with open(out_path, "w") as f:
        f.write(json.dumps(data))
