import click
from elt.main import download_and_unzip as _download_and_unzip, populate_duckdb_database as _populate_duckdb_database


@click.group("elt")
def cli():
    pass


@cli.command(name="download-and-unzip", help="Download and unzip 22 years of MapPLUTO data.")
def download_and_unzip() -> None:
    _download_and_unzip()


@cli.command(name="populate-db", help="Create a duckdb database and load 22 years of MapPLUTO data.")
def populate_duckdb_database() -> None:
    _populate_duckdb_database()


if __name__ == "__main__":
    cli()
