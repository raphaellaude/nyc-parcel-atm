# Pluto-hist API

## Set-up

For local development, add `.env` with `BASE_PATH=/path/to/directory-where-your-parquets-are-stored`

To run the server, install dependencies `poetry install` then `poetry run uvicorn main:app --reload`.

Test your running server by going to `http://127.0.0.1:8000/docs#/default` or `http://127.0.0.1:8000/items/02/40.673233/-73.952332`

To get files to the fly machine, run `flyctl ssh sftp shell` then use the `put {local_file_path} {vm_file_path}` command to upload files.
