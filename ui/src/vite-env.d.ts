/// <reference types="svelte" />
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Адрес шлюза ядра (ui/.env). */
  readonly VITE_CORE_URL: string;
}

/** Версия сборки: `v0.2.0 · 1a2b3c4* · 18.11.2026, 14:40` (vite.config.ts). */
declare const __APP_VERSION__: string;

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
