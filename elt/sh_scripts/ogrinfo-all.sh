#!/bin/bash

DIR=$1

if [ -z "$DIR" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

for file in "$DIR"/*; do
    if [ -d "$file" ]; then
        continue
    fi
    filename=$(basename -- "$file")
    filename="${filename%.*}"
    ogrinfo -so "$file" "$filename"
done
