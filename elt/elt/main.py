import os
import glob
from pandas import DataFrame
from pathlib import Path

from .assets import download_zipfiles, unzip_zipfiles, get_pluto_key
from .database import create_table, column_availibility, column_similarity
from .constants import ASSETS_DIR, YEARS


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
    col_availibility = column_availibility()
    match_df = column_similarity(col_availibility)

    print(
        "Column matches with >80 similarity, which don't exist in the same year's data: "
    )
    print(match_df)

    return match_df
