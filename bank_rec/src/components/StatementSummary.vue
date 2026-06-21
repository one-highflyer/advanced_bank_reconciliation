<script setup lang="ts">
import type { StatementSummary } from "@/types/bankRec";
import { formatMoney } from "@/utils/format";

defineProps<{
  summary: StatementSummary | null;
  selectedAmount: number | null;
  currency?: string;
  loading?: boolean;
}>();

const cards = [
  {
    key: "unreconciled_count",
    label: "Unreconciled",
  },
  {
    key: "selected_amount",
    label: "Selected",
  },
  {
    key: "cleared_balance",
    label: "Cleared balance",
  },
  {
    key: "unreconciled_total",
    label: "Unreconciled total",
  },
] as const;
</script>

<template>
  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <div
      v-for="card in cards"
      :key="card.key"
      class="min-h-[88px] rounded-lg border border-bank-line bg-white p-4 shadow-sm"
    >
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        {{ card.label }}
      </div>
      <div class="mt-2 text-2xl font-semibold text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else-if="card.key === 'unreconciled_count'">
          {{ summary.unreconciled_count }}
        </template>
        <template v-else-if="card.key === 'selected_amount'">
          {{ selectedAmount === null ? "None" : formatMoney(selectedAmount, currency) }}
        </template>
        <template v-else-if="card.key === 'cleared_balance'">
          {{ formatMoney(summary.cleared_balance, currency) }}
        </template>
        <template v-else>
          {{ formatMoney(summary.unreconciled_total, currency) }}
        </template>
      </div>
    </div>
  </section>
</template>
