"""
Pipeline for the NYC Pluto history / Parcel ATM tool.
"""

import os
import glob
import shutil
from pathlib import Path
from typing import Union
from zipfile import ZipFile
import requests

from .constants import ASSETS_DIR


def get_pluto_key(year: int, alias: str) -> str:
    """
    Returns the key for a PLUTO asset.
    """
    return f"pluto{str(year).zfill(2)}_{alias}"


def recursive_unzip(local_file_path: Union[str, Path]) -> None:
    """
    Unzips a file and recursively unzips any zips found within the unzipped directory.
    Args:
        local_file_path (str): Path to the file to be unzipped.
    """
    if isinstance(local_file_path, str):
        local_file_path = Path(local_file_path)

    unzipped_dir = local_file_path.parent / local_file_path.stem

    if not os.path.exists(unzipped_dir):
        os.makedirs(unzipped_dir)

    with ZipFile(local_file_path) as zip_file:
        for member in zip_file.namelist():
            filename = os.path.basename(member)

            if not filename:
                continue

            source = zip_file.open(member)
            target = open(os.path.join(unzipped_dir, filename), "wb")
            with source, target:
                shutil.copyfileobj(source, target)

    pattern = f"{unzipped_dir}/**/*.zip"
    zips = glob.glob(pattern, recursive=True)

    for zip_file in zips:
        recursive_unzip(zip_file)


def download_zipfiles():
    """
    Download and unzip a year of PLUTO data.
    """
    print("Downloading PLUTO data...")

    urls = [
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_02b.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_03c.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_04c.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_05d.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_06c.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_07c.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_08b.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_09v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_10v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_11v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_12v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_13v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_14v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_15v1.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_16v2.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/mappluto_17v1_1.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_mappluto_18v2_1_arc_shp.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_mappluto_19v2_arc_shp.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_mappluto_20v8_arc_shp.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_mappluto_21v3_arc_shp.zip",
        "https://www.nyc.gov/assets/planning/download/zip/data-maps/open-data/nyc_mappluto_22v2_arc_shp.zip",
        "https://s-media.nyc.gov/agencies/dcp/assets/files/zip/data-tools/bytes/nyc_mappluto_23v2_arc_shp.zip",
    ]

    outs = {}

    for idx, url in enumerate(urls, start=2):
        key = get_pluto_key(idx, "shp")
        print(f"Downloading {key}...")

        out_path = os.path.join(ASSETS_DIR, f"{key}.zip")
        r = requests.get(url, timeout=60)

        with open(out_path, "wb") as f:
            f.write(r.content)

        outs[key] = out_path

    return outs


def unzip_zipfiles(assets_dir: Union[str, Path]):
    """
    Unzip the PLUTO data.
    """
    print("Unzipping files...")

    pattern = f"{assets_dir}/**/*.zip"
    zips = glob.glob(pattern, recursive=True)
    print(zips)

    for zip_file in zips:
        print(f"Unzipping {zip_file}...")
        recursive_unzip(zip_file)
