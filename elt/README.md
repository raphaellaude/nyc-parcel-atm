# ELT

## Dependencies

- uv
- GDAL and GEOS
- Tippecanoe

Set up Dockerfile for ELT for less jank dependency management.

## Set-up

1. Install python dependencies:

```bash
uv sync
```

2. Create a `.env` file in the root directory with:

```bash
BASE_DIR=/path/to/where/you/want/your/assets/to/live
```

3. Run the pipeline:

```bash
uv run python cli.py download-and-unzip
uv run python cli.py populate-db
# harmonize-columns will prompt you for input on close matches
# so don't run off when running this command it will need you!
uv run python cli.py harmonize-columns
uv run python cli.py rename-columns
uv run python cli.py export-fgbs
uv run python cli.py export-fgbs --wgs84
uv run python cli.py export-parquet
uv run python cli.py export-neighborhoods
# requires the aws cli; set STORAGE_PROFILE, STORAGE_URI and DATA_URL to change the destination
uv run python cli.py upload
uv run python cli.py export-geojsons-for-tippecannoe
uv run python cli.py create-tilesets
uv run python cli.py create-lion-tileset
# optionally, if you changed the layers in the tilesets
uv run python cli.py get-tileset-json -o ../pluto-hist/chropleth.json
```
