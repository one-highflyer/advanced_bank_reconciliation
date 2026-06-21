<script setup lang="ts">
import type {
  BankAccount,
  BankTransaction,
  LinkedPayment,
  TransactionContext,
} from "@/types/bankRec";
import { deskRoute } from "@/utils/desk";
import { formatDate, formatMoney, signedAmountClass } from "@/utils/format";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import ExternalLink from "~icons/lucide/external-link";

const props = defineProps<{
  transaction?: BankTransaction;
  context: TransactionContext | null;
  bankAccount?: BankAccount;
  currency?: string;
  loading?: boolean;
  error?: string;
  embedded?: boolean;
}>();

defineEmits<{
  retry: [];
}>();

function fieldValue(value?: string | number | null) {
  if (value === undefined || value === null || value === "") {
    return "Not set";
  }
  return value;
}

function paymentLabel(payment: LinkedPayment) {
  const type = payment.payment_document || "Voucher";
  const name = payment.payment_entry || "Draft";
  return `${type} ${name}`;
}

function bankTransactionUrl(transaction?: BankTransaction) {
  return deskRoute("Bank Transaction", transaction?.name);
}

function paymentUrl(payment: LinkedPayment) {
  return deskRoute(payment.payment_document, payment.payment_entry);
}
</script>

<template>
  <section
    class="flex min-h-0 flex-col bg-white"
    :class="embedded ? '' : 'rounded-lg border border-bank-line shadow-sm'"
  >
    <div class="border-b border-bank-line px-4 py-3">
      <div class="text-base font-semibold text-bank-ink">Transaction</div>
      <div class="mt-1 truncate text-sm text-bank-muted">
        {{ transaction?.name || "No selection" }}
      </div>
    </div>

    <LoadingState v-if="loading" label="Loading transaction" />
    <ErrorState
      v-else-if="error"
      :message="error"
      can-retry
      @retry="$emit('retry')"
    />
    <EmptyState
      v-else-if="!transaction"
      title="No transaction selected"
      detail="Select a bank transaction from the list."
    />

    <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
      <div class="rounded-lg border border-bank-line p-4">
        <div class="text-sm text-bank-muted">{{ formatDate(transaction.date) }}</div>
        <div class="mt-2 text-lg font-semibold text-bank-ink">
          {{ transaction.description || transaction.bank_party_name || transaction.name }}
        </div>
        <div
          class="mt-3 text-2xl font-semibold"
          :class="signedAmountClass(transaction.amount)"
        >
          {{ formatMoney(transaction.amount, transaction.currency || currency) }}
        </div>
        <a
          class="mt-3 inline-flex items-center gap-2 text-sm font-medium text-bank-accent"
          :href="bankTransactionUrl(transaction)"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLink class="h-4 w-4" />
          Open bank transaction
        </a>
      </div>

      <dl class="mt-4 grid gap-3 sm:grid-cols-2">
        <div class="rounded-lg border border-bank-line p-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
            Reference
          </dt>
          <dd class="mt-1 break-words text-sm text-bank-ink">
            {{ fieldValue(transaction.reference_number) }}
          </dd>
        </div>
        <div class="rounded-lg border border-bank-line p-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
            Party
          </dt>
          <dd class="mt-1 break-words text-sm text-bank-ink">
            {{ fieldValue(transaction.party_display || transaction.party) }}
          </dd>
        </div>
        <div class="rounded-lg border border-bank-line p-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
            Bank party
          </dt>
          <dd class="mt-1 break-words text-sm text-bank-ink">
            {{ fieldValue(transaction.bank_party_name) }}
          </dd>
        </div>
        <div class="rounded-lg border border-bank-line p-3">
          <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
            Unallocated
          </dt>
          <dd class="mt-1 text-sm font-semibold text-bank-ink">
            {{
              formatMoney(
                transaction.unallocated_amount,
                transaction.currency || currency
              )
            }}
          </dd>
        </div>
        <div class="rounded-lg border border-bank-line p-3 sm:col-span-2">
          <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
            Bank account
          </dt>
          <dd class="mt-1 break-words text-sm text-bank-ink">
            {{
              context?.bank_account.account_name ||
              bankAccount?.account_name ||
              transaction.bank_account
            }}
          </dd>
        </div>
      </dl>

      <div class="mt-4 rounded-lg border border-bank-line">
        <div class="border-b border-bank-line px-3 py-2 text-sm font-semibold text-bank-ink">
          Linked payments
        </div>
        <div v-if="!context?.linked_payments.length" class="px-3 py-4 text-sm text-bank-muted">
          No linked payments
        </div>
        <div v-else class="divide-y divide-bank-line">
          <div
            v-for="payment in context.linked_payments"
            :key="`${payment.payment_document}-${payment.payment_entry}`"
            class="flex items-center justify-between gap-3 px-3 py-2 text-sm"
          >
            <a
              v-if="paymentUrl(payment)"
              class="min-w-0 truncate font-medium text-bank-accent"
              :href="paymentUrl(payment)"
              target="_blank"
              rel="noreferrer"
            >
              {{ paymentLabel(payment) }}
            </a>
            <div v-else class="min-w-0 truncate text-bank-ink">
              {{ paymentLabel(payment) }}
            </div>
            <div class="shrink-0 font-medium text-bank-ink">
              {{
                formatMoney(
                  payment.allocated_amount,
                  transaction.currency || currency
                )
              }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
