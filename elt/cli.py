import click
import duckdb

from elt.constants import DB_PATH
from elt.main import (
    create_lion_tileset as _create_lion_tileset,
)
from elt.main import (
    create_tilesets as _create_tilesets,
)
from elt.main import (
    download_and_unzip as _download_and_unzip,
)
from elt.main import (
    export_fgbs as _export_fgbs,
)
from elt.main import (
    export_for_tiling as _export_for_tiling,
)
from elt.main import (
    export_parquet as _export_parquet,
)
from elt.main import (
    get_tileset_json as _get_tileset_json,
)
from elt.main import (
    harmonize_pluto_columns as _harmonize_pluto_columns,
)
from elt.main import (
    populate_duckdb_database as _populate_duckdb_database,
)
from elt.main import (
    rename_columns as _rename_columns,
)
from elt.main import (
    upload as _upload,
)


@click.group("elt")
def cli():
    pass


@cli.command(
    name="download-and-unzip", help="Download and unzip 22 years of MapPLUTO data."
)
def download_and_unzip() -> None:
    _download_and_unzip()


@cli.command(
    name="populate-db",
    help="Create a duckdb database and load 22 years of MapPLUTO data.",
)
def populate_duckdb_database() -> None:
    _populate_duckdb_database()


@cli.command(
    name="harmonize-columns",
    help="Harmonize PLUTO columns across years.",
)
def harmonize_pluto_columns() -> None:
    match_df = _harmonize_pluto_columns()

    print("Please manually match most similar columns")

    matches: list[int | None] = []

    for col1, col2, similarity in match_df[["col1", "col2", "similarity"]].values:
        print(f"{col1} and {col2} have a similarity of {similarity}%")
        print("Are these the same column? (yes/no/exit)")
        response = click.prompt(">", type=str, default="yes")
        if response == "yes":
            matches.append(1)
        elif response == "exit":
            matches += [None] * (len(match_df) - len(matches))
        else:
            matches.append(0)

    match_df["match"] = matches
    match_df = match_df[match_df["match"].eq(1)].copy()
    match_df["rename_to"] = match_df[["col1", "col2"]].min(axis=1)

    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        DROP TABLE IF EXISTS column_matches;
        CREATE TABLE column_matches AS SELECT * FROM match_df;
    """
    )

    print("Column matches saved to column_matches table.")
    sql = "select * from column_matches"
    print(f'con.query("{sql}")')
    print(con.query(sql))


@cli.command("rename-columns", help="Rename columns based on column matches.")
def rename_columns():
    _rename_columns()  # pyright: ignore


@cli.command("export-fgbs", help="Export FGBs for each PLUTO year.")
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
@click.option("--wgs84", is_flag=True, help="Export in EPSG:4326 for publishing.")
def export_fgbs(years: list[int] | None = None, wgs84: bool = False):
    _export_fgbs(years=years, wgs84=wgs84)  # pyright: ignore


@cli.command(
    "export-parquet",
    help="Export all years as GeoParquet partitioned by borough and community district.",
)
def export_parquet():
    _export_parquet()  # pyright: ignore


@cli.command("upload", help="Upload FGBs and GeoParquet to object storage.")
def upload():
    _upload()


@cli.command("export-for-tiling", help="Export PLUTO layers for tippecannoe tiling.")
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
def export_for_tiling(years: list[int] | None = None):
    _export_for_tiling(years=years)  # pyright: ignore


@cli.command("create-tilesets", help="Create tilesets for each PLUTO year.")
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
def create_tilesets(years: list[int] | None = None):
    _create_tilesets(years=years)


@cli.command("create-lion-tileset", help="Create a street label tileset from NYC LION.")
@click.option("-v", "--version", help="LION release, e.g. 26d.", default="26d")
def create_lion_tileset(version: str):
    _create_lion_tileset(version=version)  # pyright: ignore


@cli.command("get-tileset-json", help="Get tileset json for each PLUTO year.")
@click.option(
    "-o", "--out-path", help="Output file path.", default="data.json", type=str
)
def get_tileset_json(out_path):
    _get_tileset_json(out_path)


if __name__ == "__main__":
    cli()
