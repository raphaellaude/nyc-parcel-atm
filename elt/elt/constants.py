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


MIN_YEAR, MAX_YEAR = 2, 25
YEARS = list(range(MIN_YEAR, MAX_YEAR + 1))
