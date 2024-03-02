import os

from dotenv import load_dotenv

load_dotenv()

BASE_PATH = os.getenv("BASE_PATH")
LAT_REGEX = (
    r"^(\+|-)?(?:90(?:(?:\.0{1,6})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,15})?))$"
)
LON_REGEX = r"^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,15})?))$"
YEARS_REGEX = r"\b(?:0[1-9]|1\d|2[0-3])\b"
