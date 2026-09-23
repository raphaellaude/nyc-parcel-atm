import click
import duckdb
from elt.main import (
    download_and_unzip as _download_and_unzip,
    populate_duckdb_database as _populate_duckdb_database,
    harmonize_pluto_columns as _harmonize_pluto_columns,
    rename_columns as _rename_columns,
    export_fgbs as _export_fgbs,
    export_parquet as _export_parquet,
    export_for_tiling as _export_for_tiling,
    create_tilesets as _create_tilesets,
    get_tileset_json as _get_tileset_json,
)
from elt.constants import DB_PATH
from elt.r2 import sync_to_r2 as _sync_to_r2


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

    matches = []

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
def export_fgbs(years: list[int] | None = None):
    _export_fgbs(years=years)  # pyright: ignore


@cli.command(
    "export-parquet", help="Export normalized GeoParquet files for each PLUTO year."
)
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
def export_parquet(years: list[int] | None = None):
    _export_parquet(years=years)  # pyright: ignore


@cli.command("export-for-tiling", help="Export PLUTO layers for tippecannoe tiling.")
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
def export_for_tiling(years: list[int] | None = None):
    _export_for_tiling(years=years)  # pyright: ignore


@cli.command("create-tilesets", help="Create tilesets for each PLUTO year.")
@click.option("-y", "--years", help="Years to export.", multiple=True, type=int)
def create_tilesets(years: list[int] | None = None):
    _create_tilesets(years=years)


@cli.command("get-tileset-json", help="Get tileset json for each PLUTO year.")
@click.option(
    "-o", "--out-path", help="Output file path.", default="data.json", type=str
)
def get_tileset_json(out_path):
    _get_tileset_json(out_path)


@cli.command(
    "sync-to-r2",
    help="Upload parquet, FGB and PMTiles assets plus a manifest.json to Cloudflare R2.",
)
@click.option("--dry-run", is_flag=True, help="List what would be uploaded.")
@click.option("--force", is_flag=True, help="Upload even if the remote copy matches.")
@click.option(
    "--create-bucket", is_flag=True, help="Create the bucket if it does not exist."
)
@click.option(
    "--only",
    multiple=True,
    type=click.Choice(["parquet", "fgb", "pmtiles"]),
    help="Only upload these asset types.",
)
def sync_to_r2(dry_run: bool, force: bool, create_bucket: bool, only: tuple[str, ...]):
    _sync_to_r2(dry_run=dry_run, force=force, create_bucket=create_bucket, only=only)


if __name__ == "__main__":
    cli()
