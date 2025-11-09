import "./style.css";
import * as pmtiles from "pmtiles";
import data from "./data.json";
import choropleth from "./choropleth.json";
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: "https://e405c9bd0305a5b3d13e603b05e2c619@o4506839635853312.ingest.us.sentry.io/4508115982548992",
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  // https://pluto-hist-backend-v2.fly.dev/
  tracesSampleRate: 1.0,
  tracePropagationTargets: [
    "localhost",
    /^https:\/\/pluto-hist-backend-v2\.fly\.dev/,
  ],
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});

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

const inKioskMode = import.meta.env.VITE_KIOSK === "true";

// PLUTO choropleth vars

let choroplethLayers = Object.keys(choropleth);
let prevLayer;
let activeLayer = "landuse";

// Print mode state
let printMode = false;

// Hover and selection state
let hoveredParcelId = null;
let selectedParcelId = null;

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

if (inKioskMode) {
  marker.setLngLat([0, 0]).addTo(map);
}

function setYear(year) {
  year = `20${year}`;
  const yearElement = document.getElementById("year");
  if (yearElement) {
    yearElement.innerHTML = year;
  }
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
  if (!legend || !legendTitle) {
    console.error("Legend elements not found");
    return;
  }
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
  if (!choropleth || !choropleth[choroplethLayer]) {
    console.error("Choropleth layer not found:", choroplethLayer);
    return;
  }

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
      switch (choropleth[choroplethLayer]?.numberFormat) {
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

  const title = choropleth[choroplethLayer]?.title || "Unknown";
  renderLegend(title, colors, values);
}

getLegend(activeLayer);

if (inKioskMode) {
  console.log("Running in kiosk mode");
  document.body.classList.add("kiosk");
  addAttributeToId("controls", "visibility", "visible");
  addAttributeToId("centerMarker", "visibility", "visible");
  addAttributeToId("about", "display", "none");
  addAttributeToId("first-year", "display", "none");
  addAttributeToId("prev-year", "display", "none");
  addAttributeToId("next-year", "display", "none");
  addAttributeToId("last-year", "display", "none");
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
        const spinnerElement = document.getElementById(this.elementId);
        if (spinnerElement) {
          spinnerElement.innerHTML = spinnerChars[index];
        }
        index = (index + 1) % spinnerChars.length;
      }, 100);
    }
    this.activeSpinners++;
  }

  stop() {
    this.activeSpinners--;
    if (this.activeSpinners === 0) {
      clearInterval(this.spinnerInterval);
      const spinnerElement = document.getElementById(this.elementId);
      if (spinnerElement) {
        spinnerElement.innerHTML = "&nbsp;&#10003;&nbsp;"; // Clear the spinner
      }
    }
  }
}

let spinner = new Spinner();

async function queryFeatures(year, lat, lng) {
  spinner.start();

  // should use queryRenderedFeatures to figure out if there's a feature at the point
  // before making the API call;

  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/single_year_point_lookup/${year}/${lat}/${lng}?kiosk=${import.meta.env.VITE_KIOSK || "false"}`,
  )
    .then((response) => {
      spinner.stop();
      return response;
    })
    .catch((error) => {
      spinner.stop();
      console.error("Error:", error);
      return null;
    });

  const dataElement = document.getElementById("data");
  if (!dataElement) {
    console.error("Data element not found");
    return;
  }

  if (response?.ok) {
    if (response.status === 204) {
      dataElement.innerHTML = "No data";
      return;
    }
    const data = await response.text();
    dataElement.innerHTML = data;
  } else if (response) {
    const data = await response.text();
    dataElement.innerHTML = "Uh oh!" + " " + data;
  } else {
    dataElement.innerHTML = "Network error - please try again";
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
      return null;
    });

  const receiptElement = document.getElementById("receipt");
  if (!receiptElement) {
    console.error("Receipt element not found");
    return;
  }

  console.log(response);
  if (response?.ok) {
    if (response.status === 204) {
      receiptElement.innerHTML = "No data";
      return;
    }
    const data = await response.text();
    receiptElement.innerHTML = data;
  } else if (response) {
    const data = await response.text();
    receiptElement.innerHTML = "Uh oh!" + " " + data;
  } else {
    receiptElement.innerHTML = "Network error - please try again";
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
      return null;
    });

  if (response?.ok) {
    const data = await response.text();
    console.log(data);
  } else if (response) {
    const data = await response.text();
    console.log("Uh oh!" + " " + data);
  } else {
    console.log("Network error - could not reach server");
  }
}

function fetchReceiptWithHTMX(lat, lng) {
  spinner.start();

  const receiptElement = document.getElementById("receipt");
  if (!receiptElement) {
    console.error("Receipt element not found");
    spinner.stop();
    return;
  }

  const url = `${import.meta.env.VITE_API_URL}/receipt/${lat}/${lng}?kiosk=${import.meta.env.VITE_KIOSK || "false"}`;

  // Use htmx.ajax for programmatic HTMX requests
  htmx
    .ajax("GET", url, {
      target: "#receipt",
      swap: "innerHTML",
    })
    .then(() => {
      spinner.stop();
    })
    .catch((error) => {
      spinner.stop();
      console.error("Error fetching receipt:", error);
      receiptElement.innerHTML = "Error fetching receipt - please try again";
    });
}

function togglePrintMode() {
  const printCheckbox = document.getElementById("print-mode-toggle");
  const dataElement = document.getElementById("data");
  const receiptElement = document.getElementById("receipt");

  if (!printCheckbox || !dataElement || !receiptElement) {
    console.error("Required elements not found");
    return;
  }

  printMode = printCheckbox.checked;

  if (printMode) {
    // Hide single year data, show receipt container
    dataElement.style.display = "none";
    receiptElement.style.display = "block";
    receiptElement.innerHTML = "Click on the map to get a historical report";
  } else {
    // Show single year data, hide receipt
    dataElement.style.display = "block";
    receiptElement.style.display = "none";
    receiptElement.innerHTML = "";
  }
}

map.on("load", function () {
  wakeServer();
  map.getCanvas().focus();

  if (inKioskMode) {
    marker.setLngLat(map.getCenter());
  }

  years.forEach((y, index) => {
    let isVisible = index === currentYearIndex ? "visible" : "none";
    let layerData = data[y];

    if (!layerData || !layerData.url || !layerData.id) {
      console.error("Invalid layer data for year:", y);
      return;
    }

    map.addSource(`pluto-${y}`, {
      type: "vector",
      url: `pmtiles://${import.meta.env.VITE_TILE_DIR}${layerData.url}`,
      promoteId: "bbl",
    });

    choroplethLayers.forEach((k) => {
      if (!choropleth[k]) {
        console.error("Choropleth layer not found:", k);
        return;
      }
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

    // Hover layer (light gray fill, only in non-kiosk mode)
    if (!inKioskMode) {
      map.addLayer({
        id: `${layerData.id}-hover`,
        source: `pluto-${y}`,
        "source-layer": layerData.id,
        type: "fill",
        layout: {
          visibility: isVisible,
        },
        paint: {
          "fill-color": "#333333",
          "fill-opacity": [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            0.3,
            0,
          ],
        },
        minzoom: 2,
        maxzoom: 16,
      });
    }

    // Selection layer (thin black edge)
    map.addLayer({
      id: `${layerData.id}-selected`,
      source: `pluto-${y}`,
      "source-layer": layerData.id,
      type: "line",
      layout: {
        visibility: isVisible,
      },
      paint: {
        "line-color": "#000000",
        "line-width": 2,
        "line-opacity": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          1,
          0,
        ],
      },
      minzoom: 2,
      maxzoom: 16,
    });
  });

  map.on("click", (e) => {
    const currentYearData = data[years[currentYearIndex]];

    // Clear previous selection
    if (selectedParcelId !== null && currentYearData) {
      map.setFeatureState(
        {
          source: `pluto-${years[currentYearIndex]}`,
          sourceLayer: currentYearData.id,
          id: selectedParcelId,
        },
        { selected: false },
      );
      selectedParcelId = null;
    }

    // Query for features at click point
    if (currentYearData) {
      const features = map.queryRenderedFeatures(e.point, {
        layers: choroplethLayers.map((k) => `${currentYearData.id}-${k}`),
      });

      // Set new selection
      if (features.length > 0) {
        const feature = features[0];
        selectedParcelId = feature.id;
        map.setFeatureState(
          {
            source: `pluto-${years[currentYearIndex]}`,
            sourceLayer: currentYearData.id,
            id: selectedParcelId,
          },
          { selected: true },
        );
      }
    }

    if (printMode) {
      fetchReceiptWithHTMX(e.lngLat.lat, e.lngLat.lng);
    } else {
      queryFeatures(year, e.lngLat.lat, e.lngLat.lng);
    }
  });

  // Hover handlers (only in non-kiosk mode)
  if (!inKioskMode) {
    map.on("mousemove", (e) => {
      const currentYearData = data[years[currentYearIndex]];
      if (!currentYearData) return;

      const features = map.queryRenderedFeatures(e.point, {
        layers: choroplethLayers.map((k) => `${currentYearData.id}-${k}`),
      });

      if (features.length > 0) {
        map.getCanvas().style.cursor = "pointer";

        const feature = features[0];
        const featureId = feature.id;

        if (hoveredParcelId !== null && hoveredParcelId !== featureId) {
          map.setFeatureState(
            {
              source: `pluto-${years[currentYearIndex]}`,
              sourceLayer: currentYearData.id,
              id: hoveredParcelId,
            },
            { hover: false },
          );
        }

        hoveredParcelId = featureId;
        map.setFeatureState(
          {
            source: `pluto-${years[currentYearIndex]}`,
            sourceLayer: currentYearData.id,
            id: featureId,
          },
          { hover: true },
        );
      } else {
        if (hoveredParcelId !== null) {
          map.setFeatureState(
            {
              source: `pluto-${years[currentYearIndex]}`,
              sourceLayer: currentYearData.id,
              id: hoveredParcelId,
            },
            { hover: false },
          );
          hoveredParcelId = null;
        }
        map.getCanvas().style.cursor = "";
      }
    });

    map.on("mouseleave", () => {
      if (hoveredParcelId !== null) {
        const currentYearData = data[years[currentYearIndex]];
        if (currentYearData) {
          map.setFeatureState(
            {
              source: `pluto-${years[currentYearIndex]}`,
              sourceLayer: currentYearData.id,
              id: hoveredParcelId,
            },
            { hover: false },
          );
        }
        hoveredParcelId = null;
      }
      map.getCanvas().style.cursor = "";
    });
  }

  if (inKioskMode) {
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

    if (!prevLayerData || !prevLayerData.id) {
      console.error("Invalid previous layer data for year:", curYear);
      return;
    }

    currentYearIndex += step;
    year = years[currentYearIndex];

    setYear(year);

    let layerData = data[year];
    if (!layerData || !layerData.id) {
      console.error("Invalid layer data for year:", year);
      return;
    }

    let choroId = `${layerData.id}-${nextLayer}`;
    let prevChoroId = `${prevLayerData.id}-${prevLayer}`;

    try {
      map.setLayoutProperty(choroId, "visibility", "visible");
      if (step != 0) {
        map.setLayoutProperty(`${layerData.id}-line`, "visibility", "visible");
        if (!inKioskMode) {
          map.setLayoutProperty(
            `${layerData.id}-hover`,
            "visibility",
            "visible",
          );
        }
        map.setLayoutProperty(
          `${layerData.id}-selected`,
          "visibility",
          "visible",
        );
      }

      let scalar = (1.59 - map.getZoom() / 10) * 5 + 1;
      let timeout = 500 * scalar * (step === 0 ? step : 1);

      setTimeout(() => {
        try {
          map.setLayoutProperty(prevChoroId, "visibility", "none");
          if (step != 0) {
            map.setLayoutProperty(
              `${prevLayerData.id}-line`,
              "visibility",
              "none",
            );
            if (!inKioskMode) {
              map.setLayoutProperty(
                `${prevLayerData.id}-hover`,
                "visibility",
                "none",
              );
            }
            map.setLayoutProperty(
              `${prevLayerData.id}-selected`,
              "visibility",
              "none",
            );
          }
        } catch (error) {
          console.error("Error hiding previous layer:", error);
        }
      }, timeout);
    } catch (error) {
      console.error("Error changing layer visibility:", error);
    }
  }
}

const firstYearButton = document.getElementById("first-year");
const prevYearButton = document.getElementById("prev-year");
const nextYearButton = document.getElementById("next-year");
const lastYearButton = document.getElementById("last-year");

if (firstYearButton) {
  firstYearButton.onclick = () => {
    let firstYearStep = minYear - year;
    if (firstYearStep !== 0) {
      changeLayer(firstYearStep, activeLayer, activeLayer);
    }
  };
}

if (prevYearButton) {
  prevYearButton.onclick = () => {
    changeLayer(-step, activeLayer, activeLayer);
  };
}

if (nextYearButton) {
  nextYearButton.onclick = () => {
    changeLayer(step, activeLayer, activeLayer);
  };
}

if (lastYearButton) {
  lastYearButton.onclick = () => {
    let lastYearStep = maxYear - year;
    if (lastYearStep !== 0) {
      changeLayer(lastYearStep, activeLayer, activeLayer);
    }
  };
}

const prevLayerButton = document.getElementById("prev-layer");
const nextLayerButton = document.getElementById("next-layer");

if (prevLayerButton) {
  prevLayerButton.onclick = () => {
    advanceLayer(-1);
  };
}

if (nextLayerButton) {
  nextLayerButton.onclick = () => {
    advanceLayer(1);
  };
}

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
  if (!map) {
    console.error("Map not initialized");
    return;
  }
  const center = map.getCenter();
  if (!center) {
    console.error("Could not get map center");
    return;
  }
  const { lng, lat } = center;
  console.log(lat, lng);
  await getReceipt(lat, lng);
}

if (inKioskMode) {
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
          const center = map.getCenter();
          if (center) {
            const { lng, lat } = center;
            queryFeatures(year, lat, lng);
          }
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
}

// Print mode checkbox handler
const printModeToggle = document.getElementById("print-mode-toggle");
if (printModeToggle) {
  printModeToggle.addEventListener("change", togglePrintMode);
}
