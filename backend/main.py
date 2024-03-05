"""
Parcel ATM API
"""

import os
import re
import duckdb
from dotenv import load_dotenv
from constants import LAT_REGEX, LON_REGEX, YEARS_REGEX, BASE_PATH, MIN_YEAR, MAX_YEAR
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja import render_template
from pyproj import Transformer

app = FastAPI()

load_dotenv()

origins = [
    "http://nycparcels.org",
    "https://nycparcels.org",
    "https://www.nycparcels.org",
    "http://www.nycparcels.org",
    "https://pluto-hist.fly.dev",
]

ENV = os.getenv("ENV", "dev")

if ENV == "dev":
    origins += [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH")

if DB_PATH is not None:
    conn = duckdb.connect(database=DB_PATH, read_only=True)
    conn.execute("INSTALL spatial; LOAD spatial;")

WGStoAlbersNYLI = Transformer.from_crs("EPSG:4326", "EPSG:2263")


pluto_years = {
    str(x).zfill(2): os.path.join(BASE_PATH, f"fgbs/pluto{str(x).zfill(2)}.fgb")
    for x in range(MIN_YEAR, MAX_YEAR + 1)
}


@app.get("/")
def read_root():
    return {"Hello!": "This is the Parcel ATM API."}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.get("/single_year_point_lookup/{year}/{lat}/{lon}")
def single_year_pluto(year: str, lat: str, lon: str):
    """
    Single year pluto view.
    """
    if not re.match(LON_REGEX, lon):
        raise HTTPException(detail="Invalid longitude", status_code=400)

    if not re.match(LAT_REGEX, lat):
        return HTTPException(detail="Invalid latitude", status_code=400)

    if not re.match(YEARS_REGEX, year):
        return HTTPException(detail="Invalid year", status_code=400)

    x, y = WGStoAlbersNYLI.transform(float(lat), float(lon))

    table = pluto_years.get(year)

    if table is None:
        return HTTPException(detail="Year not found", status_code=404)

    sql = render_template("spatial_join_2.sql.jinja", table=table, lat=y, lon=x)
    cursor = conn.execute(sql)

    if cursor.description is None:
        return HTTPException(detail="No cursor description", status_code=404)

    column_names = [desc[0] for desc in cursor.description]

    try:
        first_record = cursor.fetchone()
    except Exception as e:
        return HTTPException(detail=str(e), status_code=500)

    if first_record is None:
        return HTMLResponse("<p>No parcel found</p>")

    record = dict(zip(column_names, first_record))
    if "geom" in record:
        del record["geom"]

    return HTMLResponse(render_template("record_table.html.jinja", record=record))
