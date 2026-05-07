import { existsSync, readFileSync } from "node:fs";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/ui/",
  build: {
    sourcemap: false,
  },
  define: {
    __MINIAL_AGENT_BACKEND_SERVER_URL__: JSON.stringify(loadBackendServerUrl()),
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
});

function loadBackendServerUrl() {
  const configUrl = new URL("../env.ui.toml", import.meta.url);
  if (!existsSync(configUrl)) {
    return "";
  }

  const content = readFileSync(configUrl, "utf-8");
  const match = content.match(
    /^\s*server_url\s*=\s*(?:"([^"]*)"|'([^']*)')\s*$/m,
  );
  return (match?.[1] ?? match?.[2] ?? "").trim().replace(/\/+$/, "");
}
