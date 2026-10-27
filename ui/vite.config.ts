import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// Порт фиксирован: его ждёт Tauri (`build.devUrl` в src-tauri/tauri.conf.json).
const DEV_PORT = 1420;

export default defineConfig({
  plugins: [svelte()],
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    port: DEV_PORT,
    strictPort: true,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  envPrefix: ["VITE_", "TAURI_ENV_"],
  build: { target: "es2022" },
});
