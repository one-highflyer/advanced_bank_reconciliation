<script setup lang="ts">
import { computed } from "vue";
import type { StatementSummary } from "@/types/bankRec";
import { formatMoney } from "@/utils/format";

const props = defineProps<{
  summary: StatementSummary | null;
  statementBalance: string;
  currency?: string;
  loading?: boolean;
}>();

const statementBalanceNumber = computed(() => {
  if (props.statementBalance.trim() === "") {
    return null;
  }

  const value = Number(props.statementBalance);
  return Number.isFinite(value) ? value : null;
});

const difference = computed(() => {
  if (!props.summary || statementBalanceNumber.value === null) {
    return null;
  }

  return statementBalanceNumber.value - props.summary.cleared_balance;
});

const differenceClass = computed(() => {
  if (difference.value === null) {
    return "text-bank-muted";
  }

  return Math.abs(difference.value) < 0.005 ? "text-green-700" : "text-red-700";
});
</script>

<template>
  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <div class="min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Unreconciled
      </div>
      <div class="mt-2 text-2xl font-semibold text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>{{ summary.unreconciled_count }}</template>
      </div>
    </div>

    <div class="min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Unreconciled total
      </div>
      <div class="mt-2 text-2xl font-semibold text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>
          {{ formatMoney(summary.unreconciled_total, currency) }}
        </template>
      </div>
    </div>

    <div class="min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        ERP cleared balance
      </div>
      <div class="mt-2 text-2xl font-semibold text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>
          {{ formatMoney(summary.cleared_balance, currency) }}
        </template>
      </div>
    </div>

    <div class="min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Difference
      </div>
      <div class="mt-2 text-2xl font-semibold" :class="differenceClass">
        <template v-if="loading">...</template>
        <template v-else-if="difference === null">Set balance</template>
        <template v-else>
          {{ formatMoney(difference, currency) }}
        </template>
      </div>
    </div>
  </section>
</template>
