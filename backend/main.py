"""
Parcel ATM API
"""

import os
import re
import duckdb
import logging
from datetime import datetime
from numpy.random import randint
from pyogrio import read_dataframe
from dotenv import load_dotenv
from constants import (
    LAT_REGEX,
    LON_REGEX,
    YEARS_REGEX,
    BASE_DIR,
    MIN_YEAR,
    MAX_YEAR,
    BOOL_REGEX,
    SHORT_SUMMARY_COLS,
)
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja import render_template
from pyproj import Transformer
from barcode import EAN13
from barcode.errors import NumberOfDigitsError
import sentry_sdk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("Loading environment variables from .env file.")
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
    logger.info("Running in dev mode. Adding localhost origins.")
    origins += [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
else:
    logger.info("Not running in dev mode! Setting up Sentry.")
    sentry_sdk.init(
        dsn="https://ade1c60a5cd99ca0404fd00c38063620@o4506839635853312.ingest.us.sentry.io/4506839636180992",
        traces_sample_rate=1.0,
        profiles_sample_rate=0.1,
    )

logger.info("Starting Parcel ATM API")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = duckdb.connect(database=":memory:")
conn.execute("INSTALL spatial; LOAD spatial;")

WGStoAlbersNYLI = Transformer.from_crs("EPSG:4326", "EPSG:2263")


pluto_years = {
    str(x).zfill(2): os.path.join(str(BASE_DIR), f"fgbs/pluto{str(x).zfill(2)}.fgb")
    for x in range(MIN_YEAR, MAX_YEAR + 1)
}

logger.info(f"PLUTO years: {pluto_years}")


@app.get("/")
def read_root():
    return {"Hello!": "This is the Parcel ATM API."}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.get("/single_year_point_lookup/{year}/{lat}/{lon}")
def single_year_pluto(
    year: str,
    lat: str,
    lon: str,
    kiosk=Query(default=False, description="Returns a limited set of attributes"),
):
    """
    Single year pluto view.

    Parameters:
        year (str): Two digit year (e.g., "21", "05"). Supported years are 02-23
        lat (str): Latitude in decimal degrees (e.g., "40.7128")
        lon (str): Longitude in decimal degrees (e.g., "-73.9352")
        kiosk (bool): Returns a limited set of attributes. This feature is for the ATM
            running in kiosk mode so as not to overflow the screen.
    """
    if not re.match(LON_REGEX, lon):
        logger.error(f"Invalid longitude: {lon}")
        raise HTTPException(detail="Invalid longitude", status_code=400)

    if not re.match(LAT_REGEX, lat):
        logger.error(f"Invalid latitude: {lat}")
        raise HTTPException(detail="Invalid latitude", status_code=400)

    if not re.match(YEARS_REGEX, year):
        logger.error(f"Invalid year: {year}")
        raise HTTPException(detail="Invalid year", status_code=400)

    if not re.match(BOOL_REGEX, kiosk):
        logger.error(f"Invalid kiosk: {kiosk}")
        raise HTTPException(detail="Invalid kiosk", status_code=400)

    logger.info("Transforming coordinates to Albers")
    x, y = WGStoAlbersNYLI.transform(float(lat), float(lon))

    table = pluto_years.get(year)
    logger.info(f"Looking up year {year} in table {table}")

    if table is None:
        logger.error(f"Year not found: {year}")
        raise HTTPException(detail="Year not found", status_code=404)

    logger.info("Rendering SQL template")

    columns = ["*"]

    if kiosk == "true":
        columns = SHORT_SUMMARY_COLS

    sql = render_template("point_lookup.sql.jinja", table=table, columns=columns)

    logger.info(f"Looking up point ({x}, {y}) in table {table}")
    try:
        cursor = conn.execute(sql, parameters=(x, y))
    except (duckdb.SerializationException, duckdb.InvalidInputException) as e:
        logger.error(f"Serialization or InvalidInputException error: {e}")
        return HTMLResponse('<p style="color=grey">No parcel found</p>')

    if cursor.description is None:
        logger.error("No cursor description")
        raise HTTPException(detail="No cursor description", status_code=404)

    column_names = [desc[0] for desc in cursor.description]

    try:
        logger.info("Fetching first record")
        first_record = cursor.fetchone()
    except Exception as e:
        logger.error(f"Error fetching record: {e}")
        raise HTTPException(detail=str(e), status_code=500)

    if first_record is None:
        logger.info("No parcel found")
        return HTMLResponse("<p>No parcel found</p>")
    elif all(v == "" or v == 0 or v is None for v in first_record):
        logger.info("All values are None")
        return HTMLResponse("<p>No parcel found</p>")
    else:
        logger.info(f"Found parcel: {first_record}")

    record = dict(zip(column_names, first_record))

    if "geom" in record:
        logger.info("Removing geom column")
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

        svg_body = re.sub(
            r'width="([\d.]+)"', f'width="{new_width}"', svg_body, count=1
        )
        svg_body = re.sub(
            r'height="([\d.]+)"', f'height="{new_height}"', svg_body, count=1
        )

        stroke_width = re.search(r'stroke-width="([\d.]+)"', svg_body)
        if stroke_width:
            scale_factor = width / new_width
            new_stroke_width = float(stroke_width.group(1)) * scale_factor * 0.25
            svg_body = re.sub(
                r'stroke-width="([\d.]+)"',
                f'stroke-width="{new_stroke_width}"',
                svg_body,
            )

        return svg_body
    else:
        raise ValueError("Width and height not found in SVG")


def get_year_geom_svg(year, x, y):
    table = pluto_years.get(year)

    result = read_dataframe(
        table,
        columns=["geom"],
        force_2d=True,
        bbox=(x, y, x, y),
    )

    try:
        body = result.geometry[0]._repr_svg_()
    except KeyError:
        return None

    body = body.replace('fill="#66cc99"', 'fill="#ffffff"')
    body = body.replace('stroke="#555555"', 'stroke="#000000"')
    body = re.sub(r'opacity="([\d.]+)"', 'fill-opacity="0.0"', body)
    body = scale_svg(body, 75)

    return body


@app.get("/receipt/{lat}/{lon}")
def receipt(
    lat: str,
    lon: str,
    kiosk=Query(default=False, description="Returns a limited set of attributes"),
):
    """
    Returns a summary of the parcels at the input location over time including
    the intersecting parcel boundaries and other longitudinal attributes.

    Parameters:
        lat (str): The latitude of the location.
        lon (str): The longitude of the location.
        kiosk (bool): Returns the same data without receipt boilerplate
            (barcode, header, etc.).

    Returns:
        str: The summary of the parcels at the input location over time.
    """
    if not re.match(LON_REGEX, lon):
        logger.error(f"Invalid longitude: {lon}")
        raise HTTPException(detail="Invalid longitude", status_code=400)

    if not re.match(LAT_REGEX, lat):
        logger.error(f"Invalid latitude: {lat}")
        raise HTTPException(detail="Invalid latitude", status_code=400)

    logger.info("Transforming coordinates to Albers")
    x, y = WGStoAlbersNYLI.transform(float(lat), float(lon))

    svgs = {}

    logger.info("Getting SVGs")
    for year in pluto_years.keys():
        body = get_year_geom_svg(year, x, y)
        if body is not None:
            svgs[year] = body

    logger.info(f"Found {len(svgs)} SVGs for years {list(svgs.keys())}")

    if len(svgs) == 0:
        return HTMLResponse("No parcels found", status_code=404)

    address = ""

    try:
        logger.info("Getting address")
        table = pluto_years.get("25")
        cursor = conn.query(
            f"SELECT address FROM ST_Read('{table}', spatial_filter=ST_AsWKB(ST_POINT($1, $2))) LIMIT 1",
            params=(x, y),
        )
        address = cursor.fetchone()[0]
        logger.info(f"Address: {address}")
    except Exception as e:
        logger.info(f"Could not find an address: {e}")
        return HTMLResponse("Could not find an address!", status_code=404)

    address_hash = str(abs(hash(address * 3)) % (10**12))[:12]
    try:
        barcode = EAN13(address_hash)
    except NumberOfDigitsError:
        logger.error(
            f"Number of digits error getting barcode for address '{address}' and hash {address_hash}"
        )
        random_id = randint(int(10e11), int(10e12))
        barcode = EAN13(str(random_id)[:12])

    barcode_svg = barcode.render().decode("utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = render_template("receipt.sql.jinja", tables=pluto_years)

    try:
        cursor = conn.execute(sql, parameters=(x, y))
    except (duckdb.SerializationException, duckdb.InvalidInputException) as e:
        logger.error(f"Serialization error: {e}")
        return HTMLResponse('<p style="color=grey">No parcel found</p>')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(detail=f"Unexpected error {e}", status_code=500)

    if cursor.description is None:
        logger.error("No cursor description")
        raise HTTPException(detail="No cursor description", status_code=404)

    df_html = cursor.fetchdf().head(22).to_html(index=False)
    df_html = df_html.replace('border="1"', 'border="0"')
    df_html = df_html.replace("text-align: right", "text-align: left")

    _kiosk = kiosk if isinstance(kiosk, bool) else kiosk == "true"

    data = render_template(
        "receipt.html.jinja",
        lon=lon[:8],
        lat=lat[:7],
        svgs=svgs,
        address=address,
        barcode=barcode_svg,
        timestamp=timestamp,
        table=df_html,
        kiosk=_kiosk,
    )
    return HTMLResponse(content=data, status_code=200)
