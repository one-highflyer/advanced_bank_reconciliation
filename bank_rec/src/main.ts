import { createApp } from "vue";
import {
  Badge,
  Button,
  ErrorMessage,
  FormControl,
  FrappeUI,
  frappeRequest,
  setConfig,
  TabButtons,
  Tooltip,
} from "frappe-ui";
import { createPinia } from "pinia";
import App from "@/App.vue";
import { getDevBoot } from "@/services/api";
import { router } from "@/router";
import "frappe-ui/style.css";
import "@/index.css";

const globalComponents = {
  Badge,
  Button,
  ErrorMessage,
  FormControl,
  TabButtons,
  Tooltip,
};

setConfig("resourceFetcher", frappeRequest);
setConfig("fallbackErrorHandler", (error: { message?: string }) => {
  throw new Error(error.message || "Bank Rec request failed.");
});

async function loadDevBoot() {
  if (!import.meta.env.DEV || window.default_route) {
    return;
  }

  const values = await getDevBoot();
  Object.entries(values).forEach(([key, value]) => {
    window[key as keyof Window] = value as never;
  });
}

function applyTheme() {
  const themeMode = (window.desk_theme || "Light").toLowerCase();
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  const theme =
    themeMode === "automatic"
      ? prefersDark.matches
        ? "dark"
        : "light"
      : themeMode;

  document.documentElement.dataset.themeMode = themeMode;
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.nexwaveTheme = "modern";
  document.documentElement.dir = window.dir || "ltr";

  if (themeMode === "automatic") {
    prefersDark.addEventListener("change", applyTheme, { once: true });
  }
}

async function mount() {
  try {
    await loadDevBoot();
  } catch (error) {
    console.error("Unable to load development boot data.", error);
  }

  applyTheme();

  const app = createApp(App);
  app.use(FrappeUI);
  app.use(createPinia());
  app.use(router);

  Object.entries(globalComponents).forEach(([name, component]) => {
    app.component(name, component);
  });

  app.mount("#app");
}

mount();
