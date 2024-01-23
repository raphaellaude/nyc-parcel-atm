#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

DATA_DIR=$1

if [ ! -d "$DATA_DIR" ]; then
    echo "Directory $DATA_DIR does not exist"
    exit 1
fi

for parquet in "$DATA_DIR"/*.parquet; do
    filename=$(basename -- "$parquet")
    filename="${filename%.*}"
    echo "Getting layer mapping for $filename"

    python manage.py ogrinspect "$parquet" "$filename" --srid=4326 --mapping --multi

    echo "$filename = \"$parquet\"" >> data/load.py
    echo -e "\n" >> data/load.py
done
