<script setup lang="ts">
import { computed } from "vue";
import type { StatementSummary } from "@/types/bankRec";
import { formatMoney } from "@/utils/format";
import Banknote from "~icons/lucide/banknote";
import Check from "~icons/lucide/check";
import Landmark from "~icons/lucide/landmark";
import List from "~icons/lucide/list";
import Scale from "~icons/lucide/scale";

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

const isBalanced = computed(
  () => difference.value !== null && Math.abs(difference.value) < 0.005
);

const differenceClass = computed(() => {
  if (difference.value === null) {
    return "text-bank-muted";
  }

  return isBalanced.value ? "text-bank-success" : "text-red-600";
});
</script>

<template>
  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <div class="relative min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Unreconciled
      </div>
      <div class="mt-2 text-2xl font-semibold tabular-nums text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>{{ summary.unreconciled_count }}</template>
      </div>
      <div class="absolute right-4 top-4 flex h-[30px] w-[30px] items-center justify-center rounded-[9px] bg-bank-surface text-bank-muted">
        <List class="h-4 w-4" />
      </div>
    </div>

    <div class="relative min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Unreconciled total
      </div>
      <div class="mt-2 text-2xl font-semibold tabular-nums text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>
          {{ formatMoney(summary.unreconciled_total, currency) }}
        </template>
      </div>
      <div class="absolute right-4 top-4 flex h-[30px] w-[30px] items-center justify-center rounded-[9px] bg-bank-surface text-bank-muted">
        <Banknote class="h-4 w-4" />
      </div>
    </div>

    <div class="relative min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        ERP cleared balance
      </div>
      <div class="mt-2 text-2xl font-semibold tabular-nums text-bank-ink">
        <template v-if="loading">...</template>
        <template v-else-if="!summary">0</template>
        <template v-else>
          {{ formatMoney(summary.cleared_balance, currency) }}
        </template>
      </div>
      <div class="absolute right-4 top-4 flex h-[30px] w-[30px] items-center justify-center rounded-[9px] bg-bank-surface text-bank-muted">
        <Landmark class="h-4 w-4" />
      </div>
    </div>

    <div class="relative min-h-[96px] rounded-lg border border-bank-line bg-white p-4 shadow-sm">
      <div class="text-xs font-medium uppercase tracking-wide text-bank-muted">
        Difference
      </div>
      <div class="mt-2 text-2xl font-semibold tabular-nums" :class="differenceClass">
        <template v-if="loading">...</template>
        <template v-else-if="difference === null">Set balance</template>
        <template v-else>
          {{ formatMoney(difference, currency) }}
        </template>
      </div>
      <div v-if="!loading && difference !== null" class="mt-2">
        <span
          v-if="isBalanced"
          class="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-700"
        >
          <Check class="h-3.5 w-3.5" />
          Balanced
        </span>
        <span
          v-else
          class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700"
        >
          Out of balance
        </span>
      </div>
      <div class="absolute right-4 top-4 flex h-[30px] w-[30px] items-center justify-center rounded-[9px] bg-green-50 text-bank-success">
        <Scale class="h-4 w-4" />
      </div>
    </div>
  </section>
</template>
