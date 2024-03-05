import click
import duckdb
from elt.main import (
    download_and_unzip as _download_and_unzip,
    populate_duckdb_database as _populate_duckdb_database,
    harmonize_pluto_columns as _harmonize_pluto_columns,
    rename_columns as _rename_columns,
)
from elt.constants import DB_PATH


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
        print(f"Are these the same column? (yes/no/exit)")
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
    _rename_columns()


if __name__ == "__main__":
    cli()
