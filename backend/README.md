# PLUTO History backend

## Install

`poetry install`

## Running django admin commands locally

`DATABASE_URL=postgis://$user:$password@$hostname:$port/$dbname poetry run python manage.py [command]`

## Deploying to fly.io

`fly deploy`
