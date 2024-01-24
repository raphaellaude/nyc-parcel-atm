for f in "unioned/"*.parquet; do
    filename=$(basename -- "$f")
    filename="${filename%.*}"
    if [[ "$filename" != "mappluto_02b" ]]; then
        echo "$filename"
        ogr2ogr -f "Parquet" -dialect sqlite -sql "select * from $filename where geometry is not null" "cleaned/$filename".parquet "unioned/$filename".parquet
    fi
done
