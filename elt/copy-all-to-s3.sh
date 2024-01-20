for f in /Users/raphaellaude/Documents/Projects/dxd/processed_data/tiles/*.pmtiles; do
    filename=$(basename -- $f)
    echo $filename
    aws s3 cp $f "s3://pluto-hist/data/$filename"
done