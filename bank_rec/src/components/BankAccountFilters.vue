<script setup lang="ts">
import type { BankAccount, TransactionStatusFilter } from "@/types/bankRec";
import RefreshCcw from "~icons/lucide/refresh-cw";

defineProps<{
  bankAccounts: BankAccount[];
  selectedBankAccount: string;
  fromDate: string;
  toDate: string;
  status?: TransactionStatusFilter;
  showStatus?: boolean;
  loading?: boolean;
}>();

defineEmits<{
  "update:selectedBankAccount": [value: string];
  "update:fromDate": [value: string];
  "update:toDate": [value: string];
  "update:status": [value: TransactionStatusFilter];
  refresh: [];
}>();
</script>

<template>
  <section class="rounded-lg border border-bank-line bg-white p-3 shadow-sm">
    <div class="grid gap-3 md:grid-cols-[minmax(260px,1fr)_160px_160px_auto_auto] md:items-end">
      <label class="block">
        <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
          Bank account
        </span>
        <select
          class="h-10 w-full rounded-md border border-bank-line bg-white px-3 text-sm text-bank-ink outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          :value="selectedBankAccount"
          :disabled="loading || !bankAccounts.length"
          @change="$emit('update:selectedBankAccount', ($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>Select bank account</option>
          <option
            v-for="account in bankAccounts"
            :key="account.name"
            :value="account.name"
          >
            {{ account.account_name || account.name }}
          </option>
        </select>
      </label>

      <label class="block">
        <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
          From
        </span>
        <input
          class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          type="date"
          :value="fromDate"
          :max="toDate || undefined"
          :disabled="loading"
          @input="$emit('update:fromDate', ($event.target as HTMLInputElement).value)"
        />
      </label>

      <label class="block">
        <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
          To
        </span>
        <input
          class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          type="date"
          :value="toDate"
          :min="fromDate || undefined"
          :disabled="loading"
          @input="$emit('update:toDate', ($event.target as HTMLInputElement).value)"
        />
      </label>

      <label v-if="showStatus" class="block">
        <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
          Status
        </span>
        <select
          class="h-10 w-full rounded-md border border-bank-line bg-white px-3 text-sm text-bank-ink outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          :value="status"
          :disabled="loading"
          @change="$emit('update:status', ($event.target as HTMLSelectElement).value as TransactionStatusFilter)"
        >
          <option value="unreconciled">Unreconciled</option>
          <option value="reconciled">Reconciled</option>
          <option value="all">All</option>
        </select>
      </label>

      <Button
        class="h-10"
        variant="subtle"
        :loading="loading"
        @click="$emit('refresh')"
      >
        <template #prefix>
          <RefreshCcw class="h-4 w-4" />
        </template>
        Refresh
      </Button>
    </div>
  </section>
</template>
