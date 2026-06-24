<script setup lang="ts">
import type { BankTransaction } from "@/types/bankRec";
import { deskRoute } from "@/utils/desk";
import { formatDate, formatMoney, signedAmountClass } from "@/utils/format";
import ArrowDownRight from "~icons/lucide/arrow-down-right";
import ArrowUpRight from "~icons/lucide/arrow-up-right";
import ExternalLink from "~icons/lucide/external-link";

defineProps<{
  transactions: BankTransaction[];
  selectedName: string;
  currency?: string;
}>();

defineEmits<{
  select: [name: string];
}>();

function bankTransactionUrl(transaction: BankTransaction) {
  return deskRoute("Bank Transaction", transaction.name);
}

function isInflow(transaction: BankTransaction) {
  if (transaction.direction === "deposit") return true;
  if (transaction.direction === "withdrawal") return false;
  return Number(transaction.amount) > 0;
}
</script>

<template>
  <div class="divide-y divide-bank-line">
    <div
      v-for="transaction in transactions"
      :key="transaction.name"
      class="grid w-full cursor-pointer grid-cols-[120px_minmax(0,1fr)_130px_32px] gap-3 px-4 py-3 text-left transition hover:bg-blue-50/60"
      :class="
        transaction.name === selectedName
          ? 'bg-blue-50 shadow-[inset_3px_0_0_0_#0891B2]'
          : 'bg-white'
      "
      role="button"
      tabindex="0"
      @click="$emit('select', transaction.name)"
      @keydown.enter.prevent="$emit('select', transaction.name)"
      @keydown.space.prevent="$emit('select', transaction.name)"
    >
      <div class="text-sm tabular-nums text-bank-muted">
        {{ formatDate(transaction.date) }}
      </div>
      <div class="min-w-0">
        <div class="truncate text-sm font-medium text-bank-ink">
          {{ transaction.description || transaction.bank_party_name || transaction.name }}
        </div>
        <div class="mt-1 flex min-w-0 gap-2 text-xs text-bank-muted">
          <span class="truncate">{{ transaction.reference_number || "No reference" }}</span>
          <span v-if="transaction.party_display" class="truncate">
            {{ transaction.party_display }}
          </span>
        </div>
      </div>
      <div class="flex flex-col items-end">
        <div
          class="text-sm font-semibold tabular-nums"
          :class="signedAmountClass(transaction.amount)"
        >
          {{ formatMoney(transaction.amount, transaction.currency || currency) }}
        </div>
        <span
          v-if="isInflow(transaction)"
          class="mt-1 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold bg-green-50 text-green-700"
        >
          <ArrowUpRight class="h-3 w-3" />
          In
        </span>
        <span
          v-else
          class="mt-1 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold bg-gray-100 text-bank-muted"
        >
          <ArrowDownRight class="h-3 w-3" />
          Out
        </span>
      </div>
      <a
        class="inline-flex h-8 w-8 items-center justify-center rounded-md text-bank-muted transition hover:bg-white hover:text-bank-accent"
        :href="bankTransactionUrl(transaction)"
        target="_blank"
        rel="noreferrer"
        title="Open bank transaction in Desk"
        @click.stop
        @keydown.stop
      >
        <ExternalLink class="h-4 w-4" />
      </a>
    </div>
  </div>
</template>
