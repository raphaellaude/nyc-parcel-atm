import "./style.css";
import * as pmtiles from "pmtiles";
import data from "./data.json";

let protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

let years = Object.keys(data).sort();
let currentYearIndex = 0;

let year = years[currentYearIndex];

let MaxYear = years[years.length - 1];
console.log(`MaxYear: ${MaxYear}`);
let step = 1;

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
  maxBounds: [
    [-74.28851, 40.48159],
    [-73.69342, 40.9241],
  ],
});

function getZoom(map) {
  let zoom = map.getZoom();
  document.getElementById("zoom").innerHTML = zoom.toFixed(1);
}

function setYear(year) {
  year = `20${year}`;
  document.getElementById("year").innerHTML = year;
}

function addAttributeToId(elementId, attributeName, attributeValue) {
  var element = document.getElementById(elementId);
  if (element) {
    element.style[attributeName] = attributeValue;
  }
}

if (import.meta.env.VITE_KIOSK === "true") {
  console.log("Running in kiosk mode");
  document.body.classList.add("kiosk");
  addAttributeToId("controls", "visibility", "visible");
  addAttributeToId("centerMarker", "visibility", "visible");
  addAttributeToId("about", "display", "none");
  addAttributeToId("prev-year", "display", "none");
  addAttributeToId("next-year", "display", "none");
}
// hide for now while not working on vercel

class Spinner {
  constructor() {
    this.elementId = "spinner";
    this.activeSpinners = 0;
    this.spinnerInterval = null;
  }

  start() {
    if (this.activeSpinners === 0) {
      let spinnerChars = [
        ".&nbsp;&nbsp;",
        "..&nbsp;",
        "...",
        "&nbsp;..",
        "&nbsp;&nbsp;.",
        "&nbsp;&nbsp;&nbsp;",
      ];
      let index = 0;
      this.spinnerInterval = setInterval(() => {
        document.getElementById(this.elementId).innerHTML = spinnerChars[index];
        index = (index + 1) % spinnerChars.length;
      }, 100);
    }
    this.activeSpinners++;
  }

  stop() {
    this.activeSpinners--;
    if (this.activeSpinners === 0) {
      clearInterval(this.spinnerInterval);
      document.getElementById(this.elementId).innerHTML =
        "&nbsp;&#10003;&nbsp;"; // Clear the spinner
    }
  }
}

let spinner = new Spinner();

async function queryFeatures(year, lat, lng) {
  spinner.start();

  // should use queryRenderedFeatures to figure out if there's a feature at the point
  // before making the API call;

  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/single_year_point_lookup/${year}/${lat}/${lng}`,
  )
    .then((response) => {
      spinner.stop();
      return response;
    })
    .catch((error) => {
      spinner.stop();
      console.error("Error:", error);
    });

  if (response.ok) {
    if (response.status === 204) {
      document.getElementById("data").innerHTML = "No data";
      return;
    }
    const data = await response.text();
    document.getElementById("data").innerHTML = data;
  } else {
    const data = await response.text();
    document.getElementById("data").innerHTML = "Uh oh!" + " " + data;
  }
}

async function wakeServer() {
  spinner.start();

  console.log(`Fetching from API at: ${import.meta.env.VITE_API_URL}`);
  const response = await fetch(`${import.meta.env.VITE_API_URL}/healthcheck`)
    .then((response) => {
      spinner.stop();
      return response;
    })
    .catch((error) => {
      spinner.stop();
      console.error("Error:", error);
    });

  if (response.ok) {
    const data = await response.text();
    console.log(data);
  } else {
    const data = await response.text();
    console.log("Uh oh!" + " " + data);
  }
}

map.on("load", function () {
  wakeServer();

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

  // console.log(map.getStyle().layers);)

  map.on("zoom", function () {
    getZoom(map);
  });

  map.on("click", (e) => {
    queryFeatures(year, e.lngLat.lat, e.lngLat.lng);
  });
});

// map.on("mousemove", (e) => {
//   const features = map.queryRenderedFeatures(e.point);
//   if (features.length > 0) {
//     console.log(features);
//   }
// });

function advanceYear(step) {
  if (currentYearIndex + step < MaxYear - 1 && currentYearIndex + step >= 0) {
    let curYear = years[currentYearIndex];
    let prevLayerData = data[curYear];

    currentYearIndex += step;
    year = years[currentYearIndex];

    setYear(year);

    let layerData = data[year];
    map.setLayoutProperty(layerData.id, "visibility", "visible");
    map.setLayoutProperty(`${layerData.id}-line`, "visibility", "visible");

    setTimeout(() => {
      map.setLayoutProperty(prevLayerData.id, "visibility", "none");
      map.setLayoutProperty(`${prevLayerData.id}-line`, "visibility", "none");
    }, 750);
  }
}

const prevYearButton = document.getElementById("prev-year");
const nextYearButton = document.getElementById("next-year");

prevYearButton.onclick = () => {
  advanceYear(-step);
};

nextYearButton.onclick = () => {
  advanceYear(step);
};

document.onkeydown = function (e) {
  console.log(e.key);
  switch (e.key) {
    case "p":
      window.print();
      break;
    case "F13":
      window.print();
      break;
    case "a":
      advanceYear(-step);
      break;
    case "s":
      advanceYear(step);
      break;
    case "PageDown":
      advanceYear(-step);
      break;
    case "PageUp":
      advanceYear(step);
      break;
    case "q":
      if (map !== undefined) {
        const { lng, lat } = map.getCenter();
        queryFeatures(year, lat, lng);
      }
      break;
    case "w":
      // TODO: Implement change layer
      break;
    case "i":
      map.zoomIn();
      break;
    case "o":
      map.zoomOut();
      break;
  }
};
