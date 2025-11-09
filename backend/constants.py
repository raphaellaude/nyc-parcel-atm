import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getenv("BASE_DIR")
LAT_REGEX = (
    r"^(\+|-)?(?:90(?:(?:\.0{1,6})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,15})?))$"
)
LON_REGEX = r"^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,15})?))$"
YEARS_REGEX = r"\b(?:0[1-9]|1\d|2[0-5])\b"
BOOL_REGEX = r"^(true|false)?$"
MIN_YEAR, MAX_YEAR = 2, 25

SHORT_SUMMARY_COLS = [
    "address",
    "ownername",
    "yearbuilt",
    "numbldgs",
    "numfloors",
    "bldgclass",
    "zonedist1",
    "overlay1",
    "builtfar",
    "unitsres",
    "resarea",
    "comarea",
    "assessland",
    "assesstot",
    "exempttot",
    "yearalter1",
]
