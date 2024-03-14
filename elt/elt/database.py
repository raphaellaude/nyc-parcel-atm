import os
import duckdb
import functools
import pandas as pd
from thefuzz import fuzz
from itertools import combinations
from pathlib import Path
from typing import Union, Sequence

from .constants import DB_PATH, YEARS
from .jinja import render_template


def with_conn(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        conn = duckdb.connect(DB_PATH)
        conn.execute("INSTALL spatial; LOAD spatial;")

        value = func(*args, **kwargs, conn=conn)

        return value

    return wrapper_decorator


@with_conn
def create_table(alias: str, shp_files: Sequence[Union[Path, str]], conn):
    """ """
    print(f"Creating table {alias} from {shp_files}")

    if len(shp_files) == 0:
        raise ValueError(f"No shapefiles found for {alias}.")

    first_file = shp_files[0]

    conn.execute(f"CREATE TABLE {alias} AS SELECT * FROM ST_Read('{first_file}')")

    for shp_file in shp_files[1:]:
        conn.execute(f"INSERT INTO {alias} SELECT * FROM ST_Read('{shp_file}')")


@with_conn
def column_availibility(tables, conn) -> pd.DataFrame:
    """
    Get the column availibility for each year.
    """
    conn = duckdb.connect(DB_PATH)
    conn.execute("INSTALL spatial; LOAD spatial;")

    dfs: list[pd.DataFrame] = []

    for layer in tables:
        result = conn.execute(
            f"select distinct lower(column_name) as name from (describe {layer})"
        ).fetchdf()
        result.set_index("name", inplace=True)
        result[layer] = 1
        dfs.append(result)

    col_availibility = pd.concat(dfs, axis=1)
    col_availibility.fillna(0, inplace=True)
    col_availibility = col_availibility[sorted(col_availibility.columns)]

    assert isinstance(col_availibility, pd.DataFrame)

    return col_availibility


def column_similarity(col_availibility: pd.DataFrame) -> pd.DataFrame:
    """
    Get the column similarity for each year in order to harmonize across years.
    """
    consistent_cols = col_availibility.index[
        col_availibility.eq(1).all(axis=1)
    ].sort_values()
    print(
        f"""
        {len(consistent_cols)} of {len(col_availibility)} ({(len(consistent_cols) / len(col_availibility)) * 100:.1f}%)
        consistent columns found."""
    )
    partial_cols = col_availibility.index[~col_availibility.index.isin(consistent_cols)]
    combos = pd.DataFrame(
        [(a, b, fuzz.ratio(a, b)) for a, b in combinations(partial_cols, 2)],
        columns=["col1", "col2", "similarity"],
    )
    combos["not_overlapping"] = [
        col_availibility.loc[cols].sum().le(1).all()
        for cols in combos[["col1", "col2"]].values
    ]
    f = combos["similarity"].gt(80) & combos["not_overlapping"]
    match_df = (
        combos[f]
        .sort_values("similarity", ascending=False)
        .reset_index(drop=True)
        .copy()
    )

    return match_df
