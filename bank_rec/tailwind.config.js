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
          surface: "var(--nexwave-canvas)",
          panel: "var(--nexwave-surface)",
          "muted-surface": "var(--nexwave-surface-muted)",
          line: "var(--nexwave-border)",
          "line-soft": "var(--nexwave-border-soft)",
          "line-strong": "var(--nexwave-border-strong)",
          ink: "var(--nexwave-text)",
          "ink-2": "var(--nexwave-heading)",
          muted: "var(--nexwave-muted)",
          subtle: "var(--nexwave-subtle)",
          accent: "var(--nexwave-primary)",
          "accent-hover": "var(--nexwave-button-hover)",
          "accent-active": "var(--nexwave-button-active)",
          "accent-soft": "var(--nexwave-primary-soft)",
          shell: "var(--nexwave-shell)",
          "shell-deep": "var(--nexwave-sidebar)",
          "shell-line": "var(--nexwave-sidebar-border)",
          "shell-muted": "var(--nexwave-sidebar-muted)",
          "shell-hover": "var(--nexwave-sidebar-hover)",
          "shell-active": "var(--nexwave-sidebar-active)",
          "shell-accent": "var(--nexwave-shell-accent)",
          success: "var(--nexwave-success)",
          warn: "#C2410C",
        },
        // Re-point frappe-ui ramps to the NexWave palette (static utilities).
        gray:  { 50:"#F8FAFB",100:"#EDF2F4",200:"#E8EEF1",300:"#DCE4E8",400:"#B8C7CE",500:"#8FA7B2",600:"#60717B",700:"#405761",800:"#29414C",900:"#102A36" },
        blue:  { 50:"#E9F5F7",100:"#D8EEF2",200:"#B9E0E7",300:"#8FCBD6",400:"#67B2C1",500:"#0E7490",600:"#155E75",700:"#164E63",800:"#123F50",900:"#0F2A39" },
        green: { 50:"#F0FDF4",100:"#DCFCE7",200:"#BBF7D0",300:"#86EFAC",400:"#4ADE80",500:"#22C55E",600:"#16A34A",700:"#15803D",800:"#166534",900:"#14532D" },
        red:   { 50:"var(--red-50)",100:"var(--red-100)",200:"var(--red-200)",300:"var(--red-300)",400:"var(--red-400)",500:"var(--red-500)",600:"var(--red-600)",700:"var(--red-700)",800:"var(--red-800)",900:"var(--red-900)" },
        amber: { 50:"#FFF7ED",100:"#FFEDD5",200:"#FED7AA",300:"#FDBA74",400:"#FB923C",500:"#F97316",600:"#EA580C",700:"#C2410C",800:"#9A3412",900:"#7C2D12" },
      },
      borderRadius: {
        md: "6px",
        lg: "10px",
      },
      boxShadow: {
        sm: "var(--nexwave-card-shadow)",
        lg: "var(--nexwave-menu-shadow)",
        xl: "var(--nexwave-menu-shadow)",
        "bank-selected": "inset 3px 0 0 0 var(--nexwave-primary)",
      },
    },
  },
  plugins: [],
};
