import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";

// Порт фиксирован: его ждёт Tauri (`build.devUrl` в src-tauri/tauri.conf.json).
const DEV_PORT = 1420;

export default defineConfig(({ mode }) => ({
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
  // vitest (режим test) берёт клиентскую сборку Svelte: иначе руны компилируются в серверный
  // вариант без реактивности, и тест проверял бы не тот код, что работает в окне.
  resolve: mode === "test" ? { conditions: ["browser"] } : {},
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
}));
