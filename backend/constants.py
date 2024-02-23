import os
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = os.getenv("BASE_PATH")

PLUTO_YEARS = {
    "02": os.path.join(BASE_PATH, "mappluto_02b.parquet"),
    "03": os.path.join(BASE_PATH, "mappluto_03c.parquet"),
    "04": os.path.join(BASE_PATH, "mappluto_04c.parquet"),
    "05": os.path.join(BASE_PATH, "mappluto_05d.parquet"),
    "06": os.path.join(BASE_PATH, "mappluto_06c.parquet"),
    "07": os.path.join(BASE_PATH, "mappluto_07c.parquet"),
    "08": os.path.join(BASE_PATH, "mappluto_08b.parquet"),
    "09": os.path.join(BASE_PATH, "mappluto_09v2.parquet"),
    "10": os.path.join(BASE_PATH, "mappluto_10v2.parquet"),
    "11": os.path.join(BASE_PATH, "mappluto_11v2.parquet"),
    "12": os.path.join(BASE_PATH, "mappluto_12v2.parquet"),
    "13": os.path.join(BASE_PATH, "mappluto_13v2.parquet"),
    "14": os.path.join(BASE_PATH, "mappluto_14v2.parquet"),
    "15": os.path.join(BASE_PATH, "mappluto_15v1.parquet"),
    "16": os.path.join(BASE_PATH, "mappluto_16v2.parquet"),
    "17": os.path.join(BASE_PATH, "mappluto_17v1_1.parquet"),
    "18": os.path.join(BASE_PATH, "nyc_mappluto_18v2_1_arc_shp.parquet"),
    "19": os.path.join(BASE_PATH, "nyc_mappluto_19v2_arc_shp.parquet"),
    "20": os.path.join(BASE_PATH, "nyc_mappluto_20v8_arc_shp.parquet"),
    "21": os.path.join(BASE_PATH, "nyc_mappluto_21v3_arc_shp.parquet"),
    "22": os.path.join(BASE_PATH, "nyc_mappluto_22v2_arc_shp.parquet"),
    "23": os.path.join(BASE_PATH, "nyc_mappluto_23v2_arc_shp.parquet"),
}
LAT_REGEX = r'^(\+|-)?(?:90(?:(?:\.0{1,6})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,15})?))$'
LON_REGEX = r'^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,15})?))$'
YEARS_REGEX = r"\b(?:0[1-9]|1\d|2[0-3])\b"
