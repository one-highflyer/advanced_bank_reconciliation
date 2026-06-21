declare module "*.vue" {
  import type { DefineComponent } from "vue";

  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>;
  export default component;
}

declare module "~icons/*" {
  import type { Component } from "vue";

  const component: Component;
  export default component;
}

interface Window {
  csrf_token?: string;
  default_route?: string;
  site_name?: string;
  session_user?: string;
  lang?: string;
  dir?: "ltr" | "rtl";
  allowed_roles?: string[];
  settings?: Record<string, unknown>;
  accounting_dimensions?: Record<string, unknown>[];
}
