"""
Parcel ATM API
"""

import re
import duckdb

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from constants import PLUTO_YEARS, LAT_REGEX, LON_REGEX, YEARS_REGEX
from jinja import render_template

app = FastAPI()

conn = duckdb.connect(database=':memory:', read_only=False)
conn.execute("INSTALL spatial; LOAD spatial;")


@app.get("/")
def read_root():
    """
    Root view.
    """
    return {"Hello": "This is the Parcel ATM API!"}


@app.get("/items/{year}/{lat}/{lon}")
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
    column_names = [desc[0] for desc in cursor.description]
    first_record = cursor.fetchone()
    record = dict(zip(column_names, first_record))
    del record["geometry"]

    return HTMLResponse(render_template("record_table.html.jinja", record=record))
