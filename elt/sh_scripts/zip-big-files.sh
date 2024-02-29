for f in /Users/raphaellaude/Documents/Projects/dxd/processed_data/unioned/*.geojson; do
  filename=$(basename -- "$f")
  filename="${filename%.*}"
  zip $filename $f
done
