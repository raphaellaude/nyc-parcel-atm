import "./style.css";
import * as pmtiles from "pmtiles";
let protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

var map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      bk_pluto_02b: {
        type: "vector",
        url: "pmtiles://https://pluto-hist.s3.amazonaws.com/data/bk_pluto_02b2.pmtiles",
      },
    },
    layers: [
      {
        id: "pluto02b",
        source: "bk_pluto_02b",
        "source-layer": "pluto02b",
        type: "fill",
        paint: {
          "fill-color": [
            "match",
            ["get", "landUse2"],
            "01",
            "#feffa8",
            "02",
            "#fcb841",
            "03",
            "#b26e00",
            "04",
            "#ff8341",
            "05",
            "#fc2a29",
            "06",
            "#e362fa",
            "07",
            "#dfbeeb",
            "08",
            "#43a3d5",
            "09",
            "#78d271",
            "10",
            "#bab8b6",
            "11",
            "#555555",
            "#e7e7e7",
          ],
        },
        minzoom: 2,
        maxzoom: 16,
      },
    ],
  },
  center: [-73.948615, 40.6535], // starting position [lng, lat]
  zoom: 11, // starting zoom
  maxZoom: 16,
  minZoom: 6,
});
