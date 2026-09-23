# Parcel data MCP server

An [MCP](https://modelcontextprotocol.io) server, written in Go, that tells
agents how to query the normalized historical NYC parcel data (MapPLUTO
2002-2025) that the [ELT pipeline](../elt/README.md) publishes to Cloudflare R2.

It doesn't run queries itself. It answers: where are the files, what do the
columns mean, and what DuckDB SQL answers common questions.

## Tools

| tool | what it returns |
|---|---|
| `get_data_locations` | Datasets (core / full GeoParquet, FlatGeobuf, PMTiles), their URLs per year, format, CRS and, from the bucket manifest, sizes and row counts. |
| `get_schema` | Column names, types, descriptions and code tables (land use, borough, building class, owner type) for the `core` dataset, per-year columns for the `full` dataset, or a single column. Includes caveats for cross-year analysis. |
| `get_duckdb_setup` | SQL to load `spatial` + `httpfs`, set up credentials and create a `pluto` view over all years. |
| `get_example_queries` | Ready-to-run DuckDB queries, filterable by topic (`history`, `spatial`, `change`, `housing`, `zoning`, `valuation`, `ownership`, `land-use`, `export`, ...). |

Resources: `parcels://schema/core` (JSON), `parcels://manifest` (the bucket
manifest), `parcels://queries.sql` (setup + every example as one script).

Every tool takes an optional `access` argument:

- `https`: anonymous reads through the bucket's public URL (r2.dev or custom domain)
- `r2`: DuckDB's `r2://` with an R2 API token
- `s3`: `s3://` against a custom endpoint, e.g. LocalStack or MinIO

## Configuration

All environment variables are optional.

| variable | default | |
|---|---|---|
| `PARCEL_BUCKET` | `nyc-parcels` | R2 bucket name |
| `PARCEL_PREFIX` | | key prefix inside the bucket (matches `R2_PREFIX` in the ELT) |
| `PARCEL_PUBLIC_BASE_URL` | | public bucket URL, e.g. `https://pub-xxxx.r2.dev`. Enables `https` access and is the default manifest location |
| `PARCEL_R2_ACCOUNT_ID` | | filled into `r2` setup SQL |
| `PARCEL_MANIFEST_URL` | `$PARCEL_PUBLIC_BASE_URL/manifest.json` | URL or local path of the manifest written by `sync-to-r2` |
| `PARCEL_S3_ENDPOINT` | | `host:port` of an S3-compatible endpoint for `s3` access |
| `PARCEL_S3_REGION` | `us-east-1` | |
| `PARCEL_S3_USE_SSL` | `false` | |

Without a reachable manifest the server still works, falling back to the
pipeline's configured year range (2002-2025).

## Running

```bash
cd mcp
go build -o parcel-mcp ./cmd/parcel-mcp

./parcel-mcp                  # stdio
./parcel-mcp -http :8080      # streamable HTTP at /mcp, health check at /healthz
./parcel-mcp sql > queries.sql  # print setup + example SQL and exit
```

Add it to Claude Code:

```bash
claude mcp add nyc-parcels \
  -e PARCEL_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev \
  -- /path/to/parcel-mcp
```

## Local development with LocalStack

```bash
# 1. S3 stand-in for R2
docker compose -f ../elt/docker-compose.localstack.yml up -d

# 2. export and sync (see ../elt/README.md)
cd ../elt
uv run python cli.py export-parquet
R2_ENDPOINT_URL=http://localhost:4566 R2_ACCESS_KEY_ID=test R2_SECRET_ACCESS_KEY=test \
  R2_BUCKET=nyc-parcels uv run python cli.py sync-to-r2 --create-bucket

# 3. point the server at it. LocalStack serves objects anonymously, like a public bucket
cd ../mcp
PARCEL_PUBLIC_BASE_URL=http://localhost:4566/nyc-parcels PARCEL_S3_ENDPOINT=localhost:4566 \
  go run ./cmd/parcel-mcp sql > /tmp/queries.sql
duckdb < /tmp/queries.sql
```

## Tests

```bash
go test ./...
```

`TestCoreColumnsMatchELTSchema` fails if the documented columns in
`internal/catalog` drift from `elt/elt/schema.py`. Update both together.
