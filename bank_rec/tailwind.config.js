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
          surface: "#F5F7FA",
          line: "#E6EAF0",
          "line-soft": "#EEF1F6",
          ink: "#0F172A",
          "ink-2": "#1E293B",
          muted: "#64748B",
          subtle: "#94A3B8",
          accent: "#0891B2",
          "accent-hover": "#0E7490",
          "accent-50": "#ECFEFF",
          "accent-100": "#CFFAFE",
          "accent-200": "#A5F3FC",
          success: "#16A34A",
          warn: "#C2410C",
        },
        // Re-point frappe-ui ramps to the NexWave palette (static utilities)
        blue:  { 50:"#ECFEFF",100:"#CFFAFE",200:"#A5F3FC",300:"#67E8F9",400:"#22D3EE",500:"#0891B2",600:"#0E7490",700:"#155E75",800:"#155E75",900:"#164E63" },
        green: { 50:"#F0FDF4",100:"#DCFCE7",200:"#BBF7D0",300:"#86EFAC",400:"#4ADE80",500:"#22C55E",600:"#16A34A",700:"#15803D",800:"#166534",900:"#14532D" },
        red:   { 50:"#FFF1F2",100:"#FFE4E6",200:"#FECDD3",300:"#FDA4AF",400:"#FB7185",500:"#F43F5E",600:"#E11D48",700:"#BE123C",800:"#9F1239",900:"#881337" },
        amber: { 50:"#FFF7ED",100:"#FFEDD5",200:"#FED7AA",300:"#FDBA74",400:"#FB923C",500:"#F97316",600:"#EA580C",700:"#C2410C",800:"#9A3412",900:"#7C2D12" },
      },
    },
  },
  plugins: [],
};
