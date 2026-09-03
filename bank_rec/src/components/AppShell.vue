<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { useBankRecStore } from "@/stores/bankRec";
import CheckCheck from "~icons/lucide/check-check";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import FileCheck2 from "~icons/lucide/file-check-2";
import ListChecks from "~icons/lucide/list-checks";
import Table2 from "~icons/lucide/table-2";

const route = useRoute();
const store = useBankRecStore();

function isActive(to: string) {
  return route.path === to || route.path.startsWith(`${to}/`);
}

const navItems = [
  {
    label: "Reconcile",
    to: "/reconcile",
    icon: CheckCircle2,
  },
  {
    label: "Bank Coding",
    to: "/bank-coding",
    icon: Table2,
  },
  {
    label: "Matched",
    to: "/matched",
    icon: FileCheck2,
  },
  {
    label: "Rules",
    to: "/rules",
    icon: ListChecks,
  },
];

const activeTitle = computed(() => route.name?.toString() || "Reconcile");
const navbarLogo = computed(() => {
  const logo = store.boot?.settings.navbar_logo ?? window.settings?.navbar_logo;
  return typeof logo === "string" ? logo : "";
});
</script>

<template>
  <div class="flex min-h-screen flex-col bg-bank-surface text-bank-ink">
    <header
      class="sticky top-0 z-20 border-b border-bank-shell-line bg-bank-shell shadow-[0_1px_0_rgba(255,255,255,0.04),0_6px_18px_rgba(11,31,43,0.14)]"
    >
      <div
        class="mx-auto flex min-h-[64px] w-full max-w-[1920px] flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6 2xl:px-8"
      >
        <div class="flex min-w-0 items-center gap-3">
          <img
            v-if="navbarLogo"
            :src="navbarLogo"
            alt="Bank Rec"
            class="h-8 w-auto max-w-[120px] shrink-0 object-contain sm:max-w-[160px]"
          />
          <div
            v-else
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-white/15 bg-bank-shell-deep text-bank-shell-accent"
          >
            <CheckCheck class="h-5 w-5" />
          </div>
          <div class="min-w-0">
            <div class="text-xl font-semibold leading-7 tracking-[-0.015em] text-white">
              Bank Rec
            </div>
            <div class="truncate text-sm text-bank-shell-muted">
              {{ activeTitle }}
            </div>
          </div>
        </div>

        <nav
          class="bank-rec-nav-scrollbar flex max-w-full gap-1 overflow-x-auto rounded-lg border border-bank-shell-line bg-bank-shell-deep p-1"
          aria-label="Bank Rec sections"
        >
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-bank-shell-muted transition hover:bg-bank-shell-hover hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bank-shell-accent"
            active-class="bg-bank-shell-active text-white shadow-sm"
          >
            <component
              :is="item.icon"
              class="h-4 w-4"
              :class="isActive(item.to) ? 'text-bank-shell-accent' : ''"
            />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto flex min-h-0 w-full max-w-[1920px] flex-1 px-3 py-4 sm:px-4 md:px-6 2xl:px-8">
      <RouterView />
    </main>
  </div>
</template>
