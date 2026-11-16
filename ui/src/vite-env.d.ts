/// <reference types="svelte" />
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Адрес шлюза ядра (ui/.env). */
  readonly VITE_CORE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
