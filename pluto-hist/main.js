import "./style.css";
import * as pmtiles from "pmtiles";
import data from "./data.json";
import choropleth from "./choropleth.json";

let protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

// Years vars

let years = Object.keys(data).sort();
let currentYearIndex = 0;

let year = years[currentYearIndex];

let maxYear = years[years.length - 1];
let minYear = years[0];
let step = 1;

let center = [-73.983242, 40.70791];
let defaultZoom = 13;
const deltaDistance = 25;
function easing(t) {
  return t * (2 - t);
}

// PLUTO choropleth vars

let choroplethLayers = Object.keys(choropleth);
let prevLayer;
let activeLayer = "landuse";

var map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {},
    layers: [],
  },
  center: center,
  zoom: defaultZoom,
  maxZoom: 15.9,
  minZoom: 13,
  maxBounds: [
    [-74.28851, 40.48159],
    [-73.69342, 40.9241],
  ],
  keyboard: false,
  doubleClickZoom: false,
});

let marker = new maplibregl.Marker({ color: "#000000" });

if (import.meta.env.VITE_KIOSK === "true") {
  marker.setLngLat([0, 0]).addTo(map);
}

// function getZoom(map) {
//   let zoom = map.getZoom();
//   document.getElementById("zoom").innerHTML = zoom.toFixed(1);
// }

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

function renderLegend(title, colors, labels) {
  var legend = document.getElementById("legend");
  var legendTitle = document.getElementById("layer");
  legendTitle.innerHTML = title;
  let legendHTML = "";
  for (var i = 0; i < colors.length; i++) {
    legendHTML += `
    <div class="legend-item">
      <div class="legend-color" style="background-color:${colors[i]}"></div>
      <p class="legend-text">${labels[i]}</p>
    </div>`;
  }
  legend.innerHTML = legendHTML;
}

function getLegend(choroplethLayer) {
  let choroplethFill = choropleth[choroplethLayer].fillColor;

  if (choroplethFill == undefined) {
    return;
  }

  let colors = choroplethFill.slice(2).filter((c) => typeof c === "string");
  let values;

  if (choroplethFill[0] === "match") {
    values = choropleth[choroplethLayer].legend;
  } else if (choroplethFill[0] === "interpolate") {
    values = choroplethFill.slice(2).filter((c) => typeof c === "number");

    let formatter = (() => {
      switch (choropleth[choroplethLayer].numberFormat) {
        case "usd":
          return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            notation: "compact",
            compactDisplay: "short",
          });
        case "year":
          return new Intl.NumberFormat("en-US", {
            useGrouping: false,
          });
        case "int":
          return new Intl.NumberFormat("en-US", {
            style: "decimal",
            notation: "compact",
            compactDisplay: "short",
          });
        default:
          return new Intl.NumberFormat("en-US", {
            style: "decimal",
            maximumFractionDigits: 1,
          });
      }
    })();

    values = values.map((v, i) => {
      if (i === values.length - 1) {
        return `${formatter.format(v)}+`;
      }
      return `${formatter.format(v)} – ${formatter.format(values[i + 1])}`;
    });
  }

  if (colors.length != values.length) {
    console.error("Number of colors and values in legend do not match");
    return;
  }

  renderLegend(choropleth[choroplethLayer].title, colors, values);
}

getLegend(activeLayer);

if (import.meta.env.VITE_KIOSK === "true") {
  console.log("Running in kiosk mode");
  document.body.classList.add("kiosk");
  addAttributeToId("controls", "visibility", "visible");
  addAttributeToId("centerMarker", "visibility", "visible");
  addAttributeToId("about", "display", "none");
  addAttributeToId("prev-year", "display", "none");
  addAttributeToId("next-year", "display", "none");
  addAttributeToId("prev-layer", "display", "none");
  addAttributeToId("next-layer", "display", "none");
} else {
  addAttributeToId("year-label", "display", "none");
  addAttributeToId("layer-label", "display", "none");
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
    `${import.meta.env.VITE_API_URL}/single_year_point_lookup/${year}/${lat}/${lng}${import.meta.env.VITE_KIOSK === "true" ? "/?kiosk=true" : ""}`,
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

async function getReceipt(lat, lng) {
  spinner.start();

  // should use queryRenderedFeatures to figure out if there's a feature at the point
  // before making the API call;

  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/receipt/${lat}/${lng}`,
  )
    .then((response) => {
      spinner.stop();
      return response;
    })
    .catch((error) => {
      spinner.stop();
      console.error("Error:", error);
    });

  console.log(response);
  if (response.ok) {
    if (response.status === 204) {
      document.getElementById("receipt").innerHTML = "No data";
      return;
    }
    const data = await response.text();
    document.getElementById("receipt").innerHTML = data;
  } else {
    const data = await response.text();
    document.getElementById("receipt").innerHTML = "Uh oh!" + " " + data;
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
  map.getCanvas().focus();

  if (import.meta.env.VITE_KIOSK === "true") {
    marker.setLngLat(map.getCenter());
  }

  years.forEach((y, index) => {
    let isVisible = index === currentYearIndex ? "visible" : "none";
    let layerData = data[y];

    map.addSource(`pluto-${y}`, {
      type: "vector",
      url: `${import.meta.env.VITE_TILE_DIR}${layerData.url}`,
    });

    choroplethLayers.forEach((k) => {
      let fillColor = choropleth[k].fillColor;
      let choroplethIsVisible =
        index === currentYearIndex && activeLayer === k ? "visible" : "none";

      // Choropleth
      map.addLayer({
        id: `${layerData.id}-${k}`,
        source: `pluto-${y}`,
        "source-layer": layerData.id,
        type: "fill",
        layout: {
          visibility: choroplethIsVisible,
        },
        paint: {
          "fill-color": fillColor,
        },
        minzoom: 2,
        maxzoom: 16,
      });
    });

    // Line
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

  // getZoom(map);

  // map.on("zoom", function () {
  //   getZoom(map);
  // });

  map.on("click", (e) => {
    queryFeatures(year, e.lngLat.lat, e.lngLat.lng);
  });

  if (import.meta.env.VITE_KIOSK === "true") {
    map.on("move", function (e) {
      marker.setLngLat(map.getCenter());
    });
  }

  map.getCanvas().addEventListener(
    "keydown",
    (e) => {
      let scalar = (1.59 - map.getZoom() / 10) * 20 + 1;
      map.getCanvas().focus();
      e.preventDefault();
      if (e.which === 38) {
        // up
        map.panBy([0, -deltaDistance * scalar], {
          easing: easing,
        });
      } else if (e.which === 40) {
        // down
        map.panBy([0, deltaDistance * scalar], {
          easing: easing,
        });
      } else if (e.which === 37) {
        // left
        map.panBy([-deltaDistance * scalar, 0], {
          easing: easing,
        });
      } else if (e.which === 39) {
        // right
        map.panBy([deltaDistance * scalar, 0], {
          easing: easing,
        });
      }
    },
    true,
  );
});

function changeLayer(step, prevLayer, nextLayer) {
  if (currentYearIndex + step < maxYear - 1 && currentYearIndex + step >= 0) {
    let curYear = years[currentYearIndex];
    let prevLayerData = data[curYear];

    currentYearIndex += step;
    year = years[currentYearIndex];

    setYear(year);

    let layerData = data[year];
    let choroId = `${layerData.id}-${nextLayer}`;
    let prevChoroId = `${prevLayerData.id}-${prevLayer}`;

    map.setLayoutProperty(choroId, "visibility", "visible");
    if (step != 0) {
      map.setLayoutProperty(`${layerData.id}-line`, "visibility", "visible");
    }

    let scalar = (1.59 - map.getZoom() / 10) * 5 + 1;
    let timeout = 500 * scalar * (step === 0 ? step : 1);

    setTimeout(() => {
      map.setLayoutProperty(prevChoroId, "visibility", "none");
      if (step != 0) {
        map.setLayoutProperty(`${prevLayerData.id}-line`, "visibility", "none");
      }
    }, timeout);
  }
}

const prevYearButton = document.getElementById("prev-year");
const nextYearButton = document.getElementById("next-year");

prevYearButton.onclick = () => {
  changeLayer(-step, activeLayer, activeLayer);
};

nextYearButton.onclick = () => {
  changeLayer(step, activeLayer, activeLayer);
};

const prevLayerButton = document.getElementById("prev-layer");
const nextLayerButton = document.getElementById("next-layer");

prevLayerButton.onclick = () => {
  advanceLayer(-1);
};

nextLayerButton.onclick = () => {
  advanceLayer(1);
};

function mod(n, m) {
  return ((n % m) + m) % m;
}

const advanceLayer = (step) => {
  let prevLayer = activeLayer;
  let layerIndex = choroplethLayers.indexOf(activeLayer);
  let nextLayerIndex = mod(layerIndex + step, choroplethLayers.length);
  activeLayer = choroplethLayers[nextLayerIndex];

  changeLayer(0, prevLayer, activeLayer);
  getLegend(activeLayer);
};

const changeLayerFromID = (layerID) => {
  if (activeLayer === layerID) {
    return;
  }
  prevLayer = activeLayer;
  activeLayer = layerID;
  changeLayer(0, prevLayer, activeLayer);
  getLegend(activeLayer);
};

async function getReceiptFromKeyPress() {
  // get location in center screen
  const { lng, lat } = map.getCenter();
  console.log(lat, lng);
  await getReceipt(lat, lng);
}

document.onkeydown = function (e) {
  switch (e.key) {
    case "p":
      getReceiptFromKeyPress().then(() => {
        window.print();
      });
      break;
    case "F13":
      getReceiptFromKeyPress().then(() => {
        window.print();
      });
      break;
    case "b":
      // go to first year
      let firstYearStep = minYear - year;
      if (firstYearStep === 0) {
        break;
      }
      console.log(firstYearStep);
      setTimeout(() => {
        changeLayer(firstYearStep, activeLayer, activeLayer);
      }, 1000);
      break;
    case "n":
      // go to last year
      let lastYearStep = maxYear - year;
      if (lastYearStep === 0) {
        break;
      }
      console.log(lastYearStep);
      // set timeout
      setTimeout(() => {
        changeLayer(lastYearStep, activeLayer, activeLayer);
      }, 1000);
      break;
    case ",":
      changeLayer(-step, activeLayer, activeLayer);
      break;
    case ".":
      changeLayer(step, activeLayer, activeLayer);
      break;
    case "PageDown":
      changeLayer(-step, activeLayer, activeLayer);
      break;
    case "PageUp":
      changeLayer(step, activeLayer, activeLayer);
      break;
    case "q":
      if (map !== undefined) {
        const { lng, lat } = map.getCenter();
        queryFeatures(year, lat, lng);
      }
      break;
    case "u":
      changeLayerFromID("landuse");
      break;
    case "r":
      changeLayerFromID("unitsres");
      break;
    case "f":
      changeLayerFromID("builtfar");
      break;
    case "h":
      changeLayerFromID("numfloors");
      break;
    case "a":
      changeLayerFromID("yearalter1");
      break;
    case "l":
      changeLayerFromID("assessland");
      break;
    case "v":
      changeLayerFromID("assesstot");
      break;
    case "i":
      map.zoomIn();
      break;
    case "o":
      map.zoomOut();
      break;
    case "Home":
      map.flyTo({
        center: center,
        zoom: defaultZoom,
      });
      break;
    case "0":
      location.reload();
      break;
  }
};
