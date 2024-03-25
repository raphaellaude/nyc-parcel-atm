# Backend API

## Dependencies

- Poetry
- GDAL and GEOS
- Docker

## Set-up

1. Install python dependencies:

```bash
poetry install
```

2. Create a `.env` file in the root directory with:

```bash
BASE_PATH=/path/to/your/assets
```

The path to your assets should matches that used when running the pipeline.

3. Run the server:

```bash
poetry run uvicorn main:app --reload`
```

## Deployment

### Deploying to Fly.io

1. Follow their installation guide.
1. `cd backend && fly deploy`

### Uploading files to fly volume

To get files to the fly machine, run `flyctl ssh sftp shell` then use the `put {local_file_path} {vm_file_path}` command to upload files.
