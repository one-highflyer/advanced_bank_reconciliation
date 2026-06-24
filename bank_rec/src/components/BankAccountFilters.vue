<script setup lang="ts">
import { computed } from "vue";
import type { BankAccount, TransactionStatusFilter } from "@/types/bankRec";
import RefreshCcw from "~icons/lucide/refresh-cw";

const props = defineProps<{
  companies: string[];
  selectedCompany: string;
  bankAccounts: BankAccount[];
  selectedBankAccount: string;
  fromDate: string;
  toDate: string;
  statementBalance?: string;
  status?: TransactionStatusFilter;
  showStatementBalance?: boolean;
  showStatus?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:selectedCompany": [value: string];
  "update:selectedBankAccount": [value: string];
  "update:fromDate": [value: string];
  "update:toDate": [value: string];
  "update:statementBalance": [value: string];
  "update:status": [value: TransactionStatusFilter];
  refresh: [];
}>();

const companyOptions = computed(() => [
  { label: "Select company", value: "", disabled: true },
  ...props.companies.map((company) => ({
    label: company,
    value: company,
  })),
]);

const bankAccountOptions = computed(() => [
  {
    label: props.selectedCompany ? "Select bank account" : "Select company first",
    value: "",
    disabled: true,
  },
  ...props.bankAccounts.map((account) => ({
    label: account.account_name || account.name,
    value: account.name,
  })),
]);

const statusOptions = [
  { label: "Unreconciled", value: "unreconciled" },
  { label: "Reconciled", value: "reconciled" },
  { label: "All", value: "all" },
];

function updateStatementBalance(value: unknown) {
  emit(
    "update:statementBalance",
    value === null || value === undefined ? "" : String(value)
  );
}
</script>

<template>
  <section class="rounded-lg border border-bank-line bg-white p-3 shadow-sm">
    <div class="flex flex-wrap items-end gap-3">
      <FormControl
        class="min-w-[220px] flex-1"
        type="select"
        label="Company"
        variant="outline"
        size="md"
        :options="companyOptions"
        :model-value="selectedCompany"
        :disabled="loading || !companies.length"
        @update:model-value="emit('update:selectedCompany', String($event || ''))"
      />

      <FormControl
        class="min-w-[260px] flex-[1.25]"
        type="select"
        label="Bank account"
        variant="outline"
        size="md"
        :options="bankAccountOptions"
        :model-value="selectedBankAccount"
        :disabled="loading || !selectedCompany || !bankAccounts.length"
        @update:model-value="emit('update:selectedBankAccount', String($event || ''))"
      />

      <FormControl
        class="w-full tabular-nums sm:w-40"
        type="date"
        label="From"
        variant="outline"
        size="md"
        :model-value="fromDate"
        :max="toDate || undefined"
        :disabled="loading"
        @update:model-value="emit('update:fromDate', String($event || ''))"
      />

      <FormControl
        class="w-full tabular-nums sm:w-40"
        type="date"
        label="To"
        variant="outline"
        size="md"
        :model-value="toDate"
        :min="fromDate || undefined"
        :disabled="loading"
        @update:model-value="emit('update:toDate', String($event || ''))"
      />

      <FormControl
        v-if="showStatementBalance"
        class="w-full tabular-nums sm:w-48"
        type="number"
        label="Statement closing balance"
        variant="outline"
        size="md"
        placeholder="0.00"
        :model-value="statementBalance || ''"
        :disabled="loading"
        @update:model-value="updateStatementBalance"
      />

      <FormControl
        v-if="showStatus"
        class="w-full sm:w-40"
        type="select"
        label="Status"
        variant="outline"
        size="md"
        :options="statusOptions"
        :model-value="status || 'unreconciled'"
        :disabled="loading"
        @update:model-value="emit('update:status', $event as TransactionStatusFilter)"
      />

      <Button
        class="h-10 sm:ml-auto"
        variant="subtle"
        :loading="loading"
        @click="emit('refresh')"
      >
        <template #prefix>
          <RefreshCcw class="h-4 w-4" />
        </template>
        Refresh
      </Button>
    </div>
  </section>
</template>
