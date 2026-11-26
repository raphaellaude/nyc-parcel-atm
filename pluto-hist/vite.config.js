import { resolve } from "path";
import { defineConfig } from "vite";
import data from "./data.json";

export default defineConfig({
  plugins: [
    {
      name: "pluto-year-count",
      transformIndexHtml: (html) =>
        html.replaceAll("%PLUTO_YEAR_COUNT%", Object.keys(data).length),
    },
  ],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        src: resolve(__dirname, "src/about.html"),
      },
    },
  },
});
