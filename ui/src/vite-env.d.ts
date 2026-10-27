/// <reference types="svelte" />
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Адрес шлюза ядра (ui/.env). */
  readonly VITE_CORE_URL: string;
  /** Модель аватара: каталог `ui/public/avatars/<имя>/` (ADR-0011). */
  readonly VITE_AVATAR: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** Полифилл Pixi 8 для CSP без 'unsafe-eval': только побочный эффект, типов у пакета нет. */
declare module "pixi.js/unsafe-eval";
