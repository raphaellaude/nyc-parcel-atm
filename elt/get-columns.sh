#!/bin/bash

DIR="/Users/raphaellaude/Documents/Projects/dxd/processed_data/unioned"

for file in "$DIR"/*; do
    filename=$(basename -- "$file")
    filename="${filename%.*}"
    # echo "Searching $filename"
    ogrinfo -so "$file" "$filename"
done
