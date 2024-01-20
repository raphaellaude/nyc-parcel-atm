import "./style.css";
import * as pmtiles from "pmtiles";
import data from "./data.json";

let protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

let years = Object.keys(data).sort();
let currentYearIndex = 0;

let year = years[currentYearIndex];
document.getElementById("year").innerHTML = year;
// let layer = data[year];

var map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {},
    layers: [],
  },
  center: [-73.948615, 40.6535],
  zoom: 13,
  maxZoom: 15.9,
  minZoom: 13,
});

function getZoom(map) {
  let zoom = map.getZoom();
  document.getElementById("zoom").innerHTML = zoom.toFixed(1);
}

map.on("load", function () {
  years.forEach((y, index) => {
    let isVisible = index === currentYearIndex ? "visible" : "none";
    let layerData = data[y];

    map.addSource(`pluto-${y}`, {
      type: "vector",
      url: layerData.url,
    });

    map.addLayer({
      id: layerData.id,
      source: `pluto-${y}`,
      "source-layer": layerData.id,
      type: "fill",
      layout: {
        visibility: isVisible,
      },
      paint: {
        "fill-color": [
          "match",
          ["get", layerData.columns[0].id],
          "01", // 1 & 2 Family Buildings
          "#feffa8",
          "02", // Multi-Family Walk-Up Buildings
          "#fcb841",
          "03", // Multi-Family Elevator Buildings
          "#c98e0e",
          "04", // Mixed Residential & Commercial Buildings
          "#ff8341",
          "05", // Commercial & Office Buildings
          "#cc3e3d",
          "06", // Industrial & Manufacturing
          "#c26dd1",
          "07", // Transportation & Utility
          "#dfbeeb",
          "08", // Public Facilities & Institutions
          "#519dc4",
          "09", // Open Space & Outdoor Recreation
          "#699466",
          "10", // Parking Facilities
          "#bab8b6",
          "11", // Vacant Land
          "#555555",
          "#e7e7e7", // Other
        ],
      },
      minzoom: 2,
      maxzoom: 16,
    });

    map.addLayer({
      id: `${layerData.id}-line`,
      source: `pluto-${y}`,
      "source-layer": layerData.id,
      type: "line",
      layout: {
        visibility: isVisible,
      },
      paint: {
        "line-color": "#a9a9a9",
        "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.25, 16, 0.5],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0, 16, 1],
      },
      minzoom: 2,
      maxzoom: 16,
    });
  });

  getZoom(map);

  console.log(map.getStyle().layers);
});

map.on("zoom", function () {
  getZoom(map);
});

// map.on("mousemove", (e) => {
//   const features = map.queryRenderedFeatures(e.point);
//   if (features.length > 0) {
//     console.log(features);
//   }
// });

document.onkeydown = function (e) {
  switch (e.key) {
    case "p":
      window.print();
      break;
    case "a":
      if (currentYearIndex > 0) {
        let curYear = years[currentYearIndex];
        let prevLayerData = data[curYear];
        currentYearIndex -= 5;
        year = years[currentYearIndex];
        let layerData = data[year];
        document.getElementById("year").innerHTML = year;
        map.setLayoutProperty(layerData.id, "visibility", "visible");
        map.setLayoutProperty(`${layerData.id}-line`, "visibility", "visible");
        setTimeout(() => {
          map.setLayoutProperty(prevLayerData.id, "visibility", "none");
          map.setLayoutProperty(
            `${prevLayerData.id}-line`,
            "visibility",
            "none"
          );
        }, 750); // if at larger zoom levels, wait longer
      }
      break;
    case "s":
      if (currentYearIndex < years.length - 1) {
        let curYear = years[currentYearIndex];
        let prevLayerData = data[curYear];
        currentYearIndex += 5;
        year = years[currentYearIndex];
        let layerData = data[year];
        document.getElementById("year").innerHTML = year;
        map.setLayoutProperty(layerData.id, "visibility", "visible");
        map.setLayoutProperty(`${layerData.id}-line`, "visibility", "visible");
        setTimeout(() => {
          map.setLayoutProperty(prevLayerData.id, "visibility", "none");
          map.setLayoutProperty(
            `${prevLayerData.id}-line`,
            "visibility",
            "none"
          );
        }, 750); // if at larger zoom levels, wait longer
      }
      break;
    case "q":
      // TODO: Implement
      break;
    case "w":
      // TODO: Implement
      break;
    case "i":
      map.zoomIn();
      break;
    case "o":
      map.zoomOut();
      break;
  }
};
