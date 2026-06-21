<script setup lang="ts">
import type { BankTransaction } from "@/types/bankRec";
import { formatDate, formatMoney, signedAmountClass } from "@/utils/format";

defineProps<{
  transactions: BankTransaction[];
  selectedName: string;
  currency?: string;
}>();

defineEmits<{
  select: [name: string];
}>();
</script>

<template>
  <div class="divide-y divide-bank-line">
    <button
      v-for="transaction in transactions"
      :key="transaction.name"
      class="grid w-full grid-cols-[120px_minmax(0,1fr)_130px] gap-3 px-4 py-3 text-left transition hover:bg-blue-50/60"
      :class="transaction.name === selectedName ? 'bg-blue-50' : 'bg-white'"
      @click="$emit('select', transaction.name)"
    >
      <div class="text-sm text-bank-muted">
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
      <div class="text-right">
        <div
          class="text-sm font-semibold"
          :class="signedAmountClass(transaction.amount)"
        >
          {{ formatMoney(transaction.amount, transaction.currency || currency) }}
        </div>
        <div class="mt-1 text-xs capitalize text-bank-muted">
          {{ transaction.direction }}
        </div>
      </div>
    </button>
  </div>
</template>
