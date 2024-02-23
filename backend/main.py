"""
Parcel ATM API
"""

import re

import duckdb
from constants import LAT_REGEX, LON_REGEX, PLUTO_YEARS, YEARS_REGEX
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja import render_template

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://nycparcels.org",
    "https://nycparcels.org",
    "https://www.nycparcels.org",
    "http://www.nycparcels.org",
    "https://pluto-hist.fly.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


conn = duckdb.connect(database=":memory:", read_only=False)
conn.execute("INSTALL spatial; LOAD spatial;")


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

    sql = render_template(
        "spatial_join.sql.jinja", table=PLUTO_YEARS[year], lat=lat, lon=lon
    )
    cursor = conn.execute(sql)

    if cursor.description is None:
        return HTTPException(detail="No records found", status_code=404)

    column_names = [desc[0] for desc in cursor.description]

    first_record = cursor.fetchone()

    if first_record is None:
        return HTTPException(detail="No records found", status_code=404)

    record = dict(zip(column_names, first_record))
    del record["geometry"]

    return HTMLResponse(render_template("record_table.html.jinja", record=record))
