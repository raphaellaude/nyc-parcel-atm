"""
Parcel ATM API
"""

import os
import re
import duckdb
from pyogrio import read_dataframe
from dotenv import load_dotenv
from constants import LAT_REGEX, LON_REGEX, YEARS_REGEX, BASE_PATH, MIN_YEAR, MAX_YEAR
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja import render_template
from pyproj import Transformer
from barcode import EAN13

app = FastAPI()

load_dotenv()

origins = [
    "http://nycparcels.org",
    "https://nycparcels.org",
    "https://www.nycparcels.org",
    "http://www.nycparcels.org",
    "https://pluto-hist.fly.dev",
    "http://parcels.nyc",
    "http://www.parcels.nyc",
    "https://parcels.nyc",
    "https://www.parcels.nyc",
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

    try:
        cursor = conn.execute(sql)
    except duckdb.SerializationException as e:
        return HTMLResponse('<p style="color=grey">No parcel found</p>')

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


def scale_svg(svg_body, min_dimension=300):
    width_match = re.search(r'width="([\d.]+)"', svg_body)
    height_match = re.search(r'height="([\d.]+)"', svg_body)

    if width_match and height_match:
        width, height = float(width_match.group(1)), float(height_match.group(1))

        aspect_ratio = width / height

        if width > height:
            new_width = min_dimension
            new_height = min_dimension / aspect_ratio
        else:
            new_height = min_dimension
            new_width = min_dimension * aspect_ratio

        svg_body = re.sub(r'width="([\d.]+)"', f'width="{new_width}"', svg_body, count=1)
        svg_body = re.sub(r'height="([\d.]+)"', f'height="{new_height}"', svg_body, count=1)

        stroke_width = re.search(r'stroke-width="([\d.]+)"', svg_body)
        if stroke_width:
            scale_factor = width / new_width
            new_stroke_width = float(stroke_width.group(1)) * scale_factor * .5
            svg_body = re.sub(r'stroke-width="([\d.]+)"', f'stroke-width="{new_stroke_width}"', svg_body)

        return svg_body
    else:
        raise ValueError("Width and height not found in SVG")


@app.get("/receipt/{lat}/{lon}")
def receipt(lat: str, lon: str):
    """
    Single year pluto view.
    """
    if not re.match(LON_REGEX, lon):
        raise HTTPException(detail="Invalid longitude", status_code=400)

    if not re.match(LAT_REGEX, lat):
        return HTTPException(detail="Invalid latitude", status_code=400)

    x, y = WGStoAlbersNYLI.transform(float(lat), float(lon))
    year = "23"
    table = pluto_years.get(year)

    result = read_dataframe(
        table,
        columns=["address", "geom"],
        force_2d=True,
        bbox=(x, y, x, y),
    )

    try:
        svg = HTMLResponse(result.geometry[0]._repr_svg_())
    except KeyError:
        return HTTPException(detail="No parcel found", status_code=404)

    body = svg.body.decode("utf-8")
    body = body.replace("fill=\"#66cc99\"", "fill=\"#ffffff\"")
    body = body.replace("stroke=\"#555555\"", "stroke=\"#000000\"")
    body = scale_svg(body, 300)

    address = result.address[0]

    address_hash = abs(hash(address)) % (10 ** 12)
    print(address_hash)
    barcode = EAN13(str(address_hash))
    barcode_svg = barcode.render()
    print(barcode_svg)

    # svg.body = str.encode(body)

    # sql = render_template("receipt.sql.jinja", year=year, lat=y, lon=x)

    return HTMLResponse(render_template("receipt.html.jinja", svg=body, address=address, barcode=barcode_svg.decode("utf-8")))
