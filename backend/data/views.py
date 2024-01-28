"""Data views / endpoints."""

import re
from django.http import HttpResponse
from django.db import connection

from data.constants import PLUTO_BASE_TABLE_NAME
from data.converters import LAT_REGEX, LON_REGEX, YEARS_REGEX
from data.jinja import render_template


def single_year_pluto(_request, year, lon, lat):
    """
    Single year pluto view. 
    """
    if not re.match(LON_REGEX, lon):
        return HttpResponse("Invalid longitude", status=400)

    if not re.match(LAT_REGEX, lat):
        return HttpResponse("Invalid latitude", status=400)

    if not re.match(YEARS_REGEX, year):
        return HttpResponse("Invalid year", status=400)

    sql = render_template("sql/spatial_join.sql.jinja", table=f"{PLUTO_BASE_TABLE_NAME}{year}")

    cursor = connection.cursor()
    result = cursor.execute(sql, (lon, lat,))
    result = cursor.fetchall()

    if len(result) == 0:
        return HttpResponse(status=204)

    cols = [d[0] for d in cursor.description]
    html = render_template("html/record_table.html.jinja", record=zip(cols, result[0]))
    return HttpResponse(html)
