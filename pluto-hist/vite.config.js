import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        about: "src/about.html",
      },
    },
  },
});
