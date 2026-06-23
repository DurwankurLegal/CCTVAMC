import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  // Allow Vite to read test files that live in the repo-root tests/ folder.
  server: { fs: { allow: [".."] } },
  // The canonical unit tests live outside this package, so their direct bare
  // imports can't walk up to frontend/node_modules — alias them explicitly.
  // (Transitive deps resolve from the aliased package's own location.)
  resolve: {
    alias: {
      "@reduxjs/toolkit": path.resolve(__dirname, "node_modules/@reduxjs/toolkit"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: false,
    // Co-located component tests under src/ plus the canonical Redux/unit
    // tests kept in the project-root tests/ folder.
    include: [
      "src/**/*.{test,spec}.{ts,tsx}",
      "../tests/frontend/unit/**/*.{test,spec}.{ts,tsx}",
    ],
  },
});
