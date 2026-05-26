import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  js.configs.recommended,
  {
    files: ["src/**/*.ts", "src/**/*.tsx"],
    ignores: ["src/components/ui/**"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module", jsxPragma: null },
      globals: {
        // browser
        window: true, document: true, console: true, setTimeout: true,
        clearTimeout: true, setInterval: true, clearInterval: true,
        fetch: true, URL: true, URLSearchParams: true, WebSocket: true,
        Event: true, CustomEvent: true, AbortController: true,
        HTMLElement: true, HTMLDivElement: true, HTMLButtonElement: true,
        HTMLInputElement: true, HTMLTextAreaElement: true, HTMLSelectElement: true,
        HTMLSpanElement: true, HTMLTableElement: true, HTMLTableSectionElement: true,
        HTMLTableRowElement: true, HTMLTableCellElement: true,
        MutationObserver: true, ResizeObserver: true, localStorage: true,
        // React JSX transform — no need for React in scope
        React: true,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      "react-hooks": reactHooks,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
      "no-undef": "off", // TypeScript handles this
      "react-hooks/exhaustive-deps": "warn",
      "react-hooks/preserve-manual-memoization": "warn",
    },
  },
  {
    ignores: ["dist/**", "node_modules/**", "src/components/ui/**"],
  },
];
