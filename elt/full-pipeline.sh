#!/bin/bash

PROJECT_DIR="/Users/raphaellaude/Documents/Projects/dxd"

echo "Unzipping all files"
./elt/unzip-all.sh "$PROJECT_DIR/raw_data/" "$PROJECT_DIR/raw_data/shapefiles/"
# For whatever reason, 2016v2 is the zip of zips
./elt/unzip-all.sh "$PROJECT_DIR/raw_data/shapefiles/mappluto_16v2" "$PROJECT_DIR/raw_data/shapefiles/mappluto_16v2"

echo "Unioning shapefiles to parquet"
./elt/union-shapefiles.sh "$PROJECT_DIR/raw_data/shapefiles/" "$PROJECT_DIR/processed_data/unioned/"

echo "Removing shapefiles"
rm -rf "$PROJECT_DIR/raw_data/shapefiles/"

echo "Setting S3 CORS config"
aws s3api put-bucket-cors --bucket pluto-hist --cors-configuration file:///Users/raphaellaude/Documents/GitHub/pluto-hist/cors.json
