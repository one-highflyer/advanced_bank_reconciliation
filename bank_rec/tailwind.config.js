import frappeUIPreset from "frappe-ui/tailwind";

export default {
  presets: [frappeUIPreset],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    "./node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}",
    "../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}",
    "./node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}",
    "../node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}",
  ],
  safelist: [{ pattern: /!(text|bg)-/, variants: ["hover", "active"] }],
  theme: {
    extend: {
      colors: {
        bank: {
          surface: "#f7f8fa",
          line: "#d7dce2",
          ink: "#1f2933",
          muted: "#687384",
          accent: "#2563eb",
          success: "#0f8a5f",
          warn: "#b7791f",
        },
      },
    },
  },
  plugins: [],
};
