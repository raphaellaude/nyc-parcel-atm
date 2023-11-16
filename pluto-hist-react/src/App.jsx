import { useEffect } from "react";
import Map from "react-map-gl";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";

export default function App() {
  useEffect(() => {
    let protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    return () => {
      maplibregl.removeProtocol("pmtiles");
    };
  }, []);

  return (
    <div className="App">
      <Map
        style={{ width: 800, height: 600 }}
        zoom={10}
        mapStyle={{
          url: "https://demotiles.maplibre.org/style.json",
          center: [-73.948615, 40.651781],
          version: 8,
          sources: {
            sample: {
              type: "vector",
              url:
                "pmtiles://https://pluto-hist.s3.amazonaws.com/data/bk_pluto_02b.pmtiles"
            }
          },
          layers: [
            {
              id: "zcta",
              source: "sample",
              "source-layer": "zcta",
              type: "line",
              paint: {
                "line-color": "#999"
              }
            }
          ]
        }}
        mapLib={maplibregl}
      />
    </div>
  );
}