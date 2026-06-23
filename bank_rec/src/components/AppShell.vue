<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import FileCheck2 from "~icons/lucide/file-check-2";
import ListChecks from "~icons/lucide/list-checks";
import Table2 from "~icons/lucide/table-2";

const route = useRoute();

const navItems = [
  {
    label: "Reconcile",
    to: "/reconcile",
    icon: CheckCircle2,
  },
  {
    label: "Cash Coding",
    to: "/cash-coding",
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
</script>

<template>
  <div class="flex min-h-screen flex-col bg-bank-surface text-bank-ink">
    <header
      class="sticky top-0 z-20 border-b border-bank-line bg-white/95 backdrop-blur"
    >
      <div
        class="mx-auto flex min-h-[64px] w-full max-w-[1920px] flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6 2xl:px-8"
      >
        <div class="min-w-0">
          <div class="text-xl font-semibold leading-7 text-bank-ink">
            Bank Rec
          </div>
          <div class="truncate text-sm text-bank-muted">
            {{ activeTitle }}
          </div>
        </div>

        <nav
          class="flex max-w-full gap-1 overflow-x-auto rounded-lg border border-bank-line bg-gray-50 p-1"
          aria-label="Bank Rec sections"
        >
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-bank-muted transition hover:bg-white hover:text-bank-ink"
            active-class="bg-white text-bank-ink shadow-sm"
          >
            <component :is="item.icon" class="h-4 w-4" />
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
