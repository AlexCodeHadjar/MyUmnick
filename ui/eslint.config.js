import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import svelte from "eslint-plugin-svelte";
import globals from "globals";
import ts from "typescript-eslint";

import svelteConfig from "./svelte.config.js";

export default defineConfig(
  {
    // Сгенерированное не правится руками (R-64); сборки и Rust-часть — не наши исходники.
    ignores: ["dist/", "node_modules/", "src-tauri/", "src/core/protocol.gen.ts"],
  },
  js.configs.recommended,
  ts.configs.strictTypeChecked,
  ts.configs.stylisticTypeChecked,
  svelte.configs.recommended,
  {
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
        extraFileExtensions: [".svelte"],
      },
    },
  },
  {
    files: ["**/*.svelte", "**/*.svelte.ts"],
    languageOptions: { parserOptions: { parser: ts.parser, svelteConfig } },
  },
  {
    // Конфиги на JS вне tsconfig: проверка типов для них не нужна.
    files: ["**/*.js"],
    extends: [ts.configs.disableTypeChecked],
  },
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error", // R-62
      "@typescript-eslint/consistent-type-assertions": ["error", { assertionStyle: "never" }],
    },
  },
);
