import os
import glob
from pathlib import Path

from .assets import download_zipfiles, unzip_zipfiles, get_pluto_key
from .database import create_db, create_table
from .constants import ASSETS_DIR, YEARS


def download_and_unzip() -> None:
    """
    Download, unzip, and load PLUTO data into duckdb database.
    """
    zip_files = download_zipfiles()
    print(zip_files)
    unzip_zipfiles(ASSETS_DIR)


def populate_duckdb_database() -> None:
    create_db()
    for year in YEARS:
        alias = get_pluto_key(year, "shp")
        shp_dir = Path(os.path.join(ASSETS_DIR, alias))
        print(f"Shp dir: {shp_dir}")
        shp_files = list(shp_dir.glob("**/*mappluto.shp", case_sensitive=False))
        print(f"Found {len(shp_files)} shapefiles for {alias}.")
        create_table(alias, shp_files)
