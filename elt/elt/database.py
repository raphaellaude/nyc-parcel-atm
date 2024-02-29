import os
import duckdb
from pathlib import Path
from typing import Union, Sequence

from .constants import DB_PATH


def create_db(db_path: str = DB_PATH):
    con = duckdb.connect(db_path)

    con.execute(
        """
        INSTALL spatial;
        LOAD spatial;
    """
    )



def create_table(alias: str, shp_files: Sequence[Union[Path, str]]):
    con = duckdb.connect(DB_PATH)

    con.execute(
        """
        INSTALL spatial;
        LOAD spatial;
    """
    )

    print(f"Creating table {alias} from {shp_files}")

    if len(shp_files) == 0:
        raise ValueError(f"No shapefiles found for {alias}.")

    first_file = shp_files[0]

    con.execute(f"CREATE TABLE {alias} AS SELECT * FROM ST_Read('{first_file}')")

    for shp_file in shp_files[1:]:
        con.execute(f"INSERT INTO {alias} SELECT * FROM ST_Read('{shp_file}')")
