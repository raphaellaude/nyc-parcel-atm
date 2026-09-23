# ELT

## Dependencies

- uv
- GDAL and GEOS
- Tippecanoe

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
uv run python cli.py export-geojsons-for-tippecannoe
uv run python cli.py create-tilesets
# optionally, if you changed the layers in the tilesets
uv run python cli.py get-tileset-json -o ../pluto-hist/chropleth.json
# normalized GeoParquet for analysis (see below)
uv run python cli.py export-parquet
```

## Publishing to Cloudflare R2

`export-parquet` writes two hive-partitioned GeoParquet datasets to `$BASE_DIR/assets/parquet`:

- `core/year=YYYY/data.parquet`: columns present in every year, cast to the
  canonical types in [`elt/schema.py`](./elt/schema.py), plus derived `year`,
  `bbl`, `lon`, `lat` columns. Geometry is reprojected to EPSG:4326. Every year
  can be queried together.
- `full/year=YYYY/data.parquet`: every harmonized column for that year with its
  source type.

`sync-to-r2` uploads the parquet, FGB and PMTiles assets plus a `manifest.json`
(years, sizes, row counts, per-year columns) to an R2 bucket:

```
manifest.json
parquet/core/year=YYYY/data.parquet
parquet/full/year=YYYY/data.parquet
fgb/plutoYY.fgb
pmtiles/plutoYY_shp_wgs.pmtiles
```

Files whose sha256 matches the copy in the bucket are skipped, so re-running
only uploads what changed. Remote objects are never deleted.

Add these to `.env` (create an R2 API token with Object Read & Write on the bucket):

```bash
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=nyc-parcels
# optional
R2_PREFIX=                 # key prefix inside the bucket
R2_PUBLIC_BASE_URL=        # e.g. https://pub-xxxx.r2.dev, recorded in the manifest
```

```bash
uv run python cli.py sync-to-r2 --dry-run   # list what would be uploaded
uv run python cli.py sync-to-r2             # upload
uv run python cli.py sync-to-r2 --only parquet
```

The [parcel data MCP server](../mcp/README.md) documents how to query the
published data.

### Developing against LocalStack

No R2 credentials needed: run LocalStack as an S3-compatible stand-in and set
`R2_ENDPOINT_URL`, which takes precedence over `R2_ACCOUNT_ID`.

```bash
docker compose -f docker-compose.localstack.yml up -d
R2_ENDPOINT_URL=http://localhost:4566 R2_ACCESS_KEY_ID=test R2_SECRET_ACCESS_KEY=test \
  R2_BUCKET=nyc-parcels uv run python cli.py sync-to-r2 --create-bucket
```
