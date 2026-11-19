/** Версия сборки для показа в окнах: номер, коммит и время запуска (vite.config.ts). */
export const APP_VERSION: string = typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev";
