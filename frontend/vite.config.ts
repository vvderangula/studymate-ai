/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Tailwind's config is not always re-read by a running dev server (notably on
// Windows), which surfaces as "The `x` class does not exist". Restart instead.
function restartOnTailwindConfig(): Plugin {
  return {
    name: "restart-on-tailwind-config",
    apply: "serve",
    configureServer(server) {
      server.watcher.add("tailwind.config.js");
      server.watcher.on("change", (file) => {
        if (file.replace(/\\/g, "/").endsWith("/tailwind.config.js")) {
          server.config.logger.info("tailwind.config.js changed, restarting…");
          void server.restart();
        }
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), restartOnTailwindConfig()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
  },
});
