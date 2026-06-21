import vue from "@vitejs/plugin-vue";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import {
  getLocalFrappeUIDevConfig,
  importFrappeUIPlugin,
} from "./vite-helpers";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(async ({ mode }) => {
  const { useLocalFrappeUI, localFrappeUIAliases } = getLocalFrappeUIDevConfig({
    mode,
    rootDir,
  });

  const frappeui = await importFrappeUIPlugin({ useLocalFrappeUI });

  return {
    plugins: [
      frappeui({
        frappeProxy: true,
        lucideIcons: true,
        jinjaBootData: true,
        buildConfig: {
          outDir: "../advanced_bank_reconciliation/public/bank_rec",
          emptyOutDir: true,
          indexHtmlPath:
            "../advanced_bank_reconciliation/www/bank_rec/index.html",
        },
      }),
      vue(),
    ],
    server: {
      allowedHosts: true,
      fs: {
        allow: [".."],
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(rootDir, "src"),
        "tailwind.config.js": path.resolve(rootDir, "tailwind.config.js"),
        ...localFrappeUIAliases,
      },
    },
    optimizeDeps: {
      include: ["feather-icons", "tailwind.config.js"],
      exclude: ["frappe-ui"],
    },
  };
});
