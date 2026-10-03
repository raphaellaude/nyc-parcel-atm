import "./style.css";
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

// MapLibre needs WebGL. Browsers with hardware acceleration off or a
// blocklisted GPU can't create a context, so probe first and show a
// message instead of a blank map and an uncaught error.
function supportsWebGL() {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    gl?.getExtension("WEBGL_lose_context")?.loseContext();
    return !!gl;
  } catch {
    return false;
  }
}

function showWebGLUnavailable() {
  const mapElement = document.getElementById("map");
  if (mapElement) {
    mapElement.classList.add("map-unavailable");
    mapElement.innerHTML = `
      <div class="map-unavailable-message">
        <h3 class="title">The map can't load in this browser</h3>
        <p>
          It needs WebGL, which is turned off or unavailable here. Try enabling
          hardware acceleration in your browser settings, updating your
          browser, or opening the page in a different browser.
        </p>
      </div>`;
  }
  document.getElementById("spinner")?.remove();
}

if (supportsWebGL()) {
  import("./app.js");
} else {
  showWebGLUnavailable();
}
