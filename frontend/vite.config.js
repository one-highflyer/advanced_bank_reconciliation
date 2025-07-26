import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import frappeui from "frappe-ui/vite";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        outDir: `../advanced_bank_reconciliation/public/frontend`,
        emptyOutDir: true,
        indexHtmlPath: "../advanced_bank_reconciliation/www/advanced_bank_reconciliation/index.html",
      },
    }),
    vue(),
    vueJsx(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
    },
  },
  optimizeDeps: {
    include: [
      "feather-icons",
      "tailwind.config.js",
      "prosemirror-state",
      "prosemirror-view",
      "lowlight",
      "interactjs",
    ],
    esbuildOptions: {
      target: 'es2020',
    },
  },
  define: {
    global: 'globalThis',
  },
});
