#/bin/bash

for f in nyc_mappluto_23v2_arc_shp nyc_mappluto_22v2_arc_shp nyc_mappluto_21v3_arc_shp nyc_mappluto_20v8_arc_shp nyc_mappluto_19v2_arc_shp nyc_mappluto_18v2_1_arc_shp mappluto_17v1_1 mappluto_16v2 mappluto_15v1 mappluto_14v2 mappluto_13v2 mappluto_12v2 mappluto_11v2 mappluto_10v2 mappluto_09v2 mappluto_08b mappluto_07c; do
    tippecanoe -z 13 -o "$DATA_DIR/tiles/$f.pmtiles" --coalesce-smallest-as-needed --extend-zooms-if-still-dropping --include=LandUse --force -l "$f" "$DATA_DIR/unioned/$f.geojson"
done

# tippecanoe -z 13 -o "../tiles/$(date +%Y-%m-%d)_pluto02.pmtiles" --coalesce-smallest-as-needed --extend-zooms-if-still-dropping --include=LandUse --include=zonedist1 --include=bldgclass --include=assessland --force -l "pluto02" mappluto_02b.geojson
