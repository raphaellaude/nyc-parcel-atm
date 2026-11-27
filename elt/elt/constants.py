"""
This file contains the constants used in the project.
"""

import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.environ.get("BASE_DIR")

if BASE_DIR is not None:
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    DB_PATH = os.path.join(BASE_DIR, "pluto_hist.db")
    if not os.path.exists(ASSETS_DIR):
        print(f"Creating ASSETS_DIR: {ASSETS_DIR}")
        os.makedirs(ASSETS_DIR, exist_ok=True)
else:
    raise Exception("BASE_DIR environment variable not set.")


STORAGE_PROFILE = os.environ["STORAGE_PROFILE"]
STORAGE_URI = os.environ.get("STORAGE_URI", "s3://parcels-nyc")
DATA_URL = os.environ.get("DATA_URL", "https://data.parcels.nyc")

MIN_YEAR, MAX_YEAR = 2, 26
YEARS = list(range(MIN_YEAR, MAX_YEAR + 1))
