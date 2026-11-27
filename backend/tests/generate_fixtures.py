import os

import pyogrio
from dotenv import load_dotenv
from pyproj import Transformer

load_dotenv()

BASE_DIR = os.environ["BASE_DIR"]
OUT_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "fgbs")
YEARS = ["25", "26"]
LAT, LON = 40.7406, -73.9897
BOROUGH, BLOCK = "MN", 850

x, y = Transformer.from_crs("EPSG:4326", "EPSG:2263").transform(LAT, LON)
os.makedirs(OUT_DIR, exist_ok=True)

for year in YEARS:
    df = pyogrio.read_dataframe(
        os.path.join(BASE_DIR, "fgbs", f"pluto{year}.fgb"),
        bbox=(x - 2000, y - 2000, x + 2000, y + 2000),
        where=f"borough = '{BOROUGH}' AND block = {BLOCK}",
    )
    out_path = os.path.join(OUT_DIR, f"pluto{year}.fgb")
    if os.path.exists(out_path):
        os.remove(out_path)
    pyogrio.write_dataframe(df, out_path, driver="FlatGeobuf", SPATIAL_INDEX="YES")
    print(f"Wrote {len(df)} parcels to {out_path}")
