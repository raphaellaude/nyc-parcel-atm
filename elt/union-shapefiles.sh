#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <directory> <filenameination>"
    exit 1
fi

DIR=$1

if [ ! -d "$DIR" ]; then
    echo "Directory $DIR does not exist"
    exit 1
fi

DEST=$2

if [ ! -d "$DEST" ]; then
    mkdir "$DEST"
fi

PATTERN=".*mappluto\.shp"

union_shapefiles() {
    local filename="$1"
    shift
    local first="$1"
    shift

    temp_outfile="$DEST/$filename.shp"
    outfile="$DEST/$filename"

    echo "Unioning $first to $filename"
    ogr2ogr -t_srs EPSG:4326 -f 'ESRI Shapefile' "$temp_outfile" "$first" -makevalid

    ogrinfo "$temp_outfile" | grep -E '1:'

    for file in "$@"; do
        echo "Appending $file to $filename"
        ogr2ogr -t_srs EPSG:4326 -f 'ESRI Shapefile' -append "$temp_outfile" "$file" -nln "$filename" -makevalid
    done

    echo "Converting $filename"

    ogr2ogr -f 'GeoJSON' "$outfile".geojson "$temp_outfile"
    ogr2ogr -f 'Parquet' "$outfile".parquet "$temp_outfile"

    for shp_end in shp shx dbf prj; do
        rm "$DEST/$filename.$shp_end"
    done
}

for subdir in "$DIR"/*; do
    if [ -d "$subdir" ]; then
        filename=$(basename -- "$subdir")
        filename="${filename%.*}"
        echo "Searching $filename"

        map_files=()

        while IFS= read -r -d $'\0' file; do
            map_files+=("$file")
        done < <(find "$subdir" -type f -iregex ".*/$PATTERN" -print0)

        num_files=${#map_files[@]}

        case $num_files in
            1)
                echo "Found 1 file"
                union_shapefiles "$filename" "${map_files[@]}"
                ;;
            5)
                echo "Found 5 files"
                union_shapefiles "$filename" "${map_files[@]}"
                ;;
            *) 
                echo "Error: Found $num_files files, expected 5" >&2
                exit 1
                ;;
        esac
    fi
done
