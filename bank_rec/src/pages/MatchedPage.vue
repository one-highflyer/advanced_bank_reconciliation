<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BankAccountFilters from "@/components/BankAccountFilters.vue";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import {
  getMatchedTransactions,
  unreconcileTransaction,
} from "@/services/api";
import { useBankRecStore } from "@/stores/bankRec";
import type { BankTransaction, LinkedPayment } from "@/types/bankRec";
import { deskRoute } from "@/utils/desk";
import { formatDate, formatMoney, signedAmountClass } from "@/utils/format";
import ExternalLink from "~icons/lucide/external-link";
import RotateCcw from "~icons/lucide/rotate-ccw";

const store = useBankRecStore();
const route = useRoute();
const router = useRouter();

const rows = ref<BankTransaction[]>([]);
const selectedName = ref("");
const loading = ref(false);
const submittingName = ref("");
const pageError = ref("");
const pendingUnreconcile = ref<boolean | null>(null);
const loadRequestId = ref(0);

const selectedRow = computed(() =>
  rows.value.find((row) => row.name === selectedName.value)
);
const selectedLinkedPayments = computed(() =>
  selectedRow.value ? linkedPaymentsForRow(selectedRow.value) : []
);
const pendingUnreconcileMessage = computed(() =>
  pendingUnreconcile.value
    ? "Unreconcile this transaction and cancel linked Payment Entry or Journal Entry documents?"
    : "Unreconcile this transaction and keep linked documents submitted?"
);

function linkedPaymentsForRow(row: BankTransaction): LinkedPayment[] {
  if (row.linked_payments?.length) {
    return row.linked_payments;
  }
  if (row.payment_document && row.payment_entry) {
    return [
      {
        payment_document: row.payment_document,
        payment_entry: row.payment_entry,
        allocated_amount: row.allocated_amount,
      },
    ];
  }
  return [];
}

function linkedPaymentCount(row: BankTransaction) {
  return linkedPaymentsForRow(row).length;
}

function linkedVoucherCountLabel(count: number) {
  return `${count} linked ${count === 1 ? "voucher" : "vouchers"}`;
}

function linkedPaymentLabel(payment: LinkedPayment) {
  return `${payment.payment_document || "Voucher"} ${payment.payment_entry || ""}`.trim();
}

function bankTransactionUrl(row?: BankTransaction) {
  return deskRoute("Bank Transaction", row?.name);
}

function voucherUrl(payment: LinkedPayment) {
  return deskRoute(payment.payment_document, payment.payment_entry);
}

async function replaceQuery() {
  await router.replace({
    path: route.path,
    query: {
      company: store.selectedCompany || undefined,
      bank_account: store.selectedBankAccount || undefined,
      from_date: store.fromDate || undefined,
      to_date: store.toDate || undefined,
      bank_transaction: selectedName.value || undefined,
    },
  });
}

async function loadRows() {
  if (!store.selectedBankAccount) {
    rows.value = [];
    selectedName.value = "";
    await replaceQuery();
    return;
  }

  const requestId = Date.now();
  loadRequestId.value = requestId;
  loading.value = true;
  pageError.value = "";
  try {
    const response = await getMatchedTransactions({
      bank_account: store.selectedBankAccount,
      from_date: store.fromDate,
      to_date: store.toDate,
    });
    if (loadRequestId.value !== requestId) {
      return;
    }
    rows.value = response.rows;
    if (
      selectedName.value &&
      !rows.value.some((row) => row.name === selectedName.value)
    ) {
      selectedName.value = "";
    }
    if (!selectedName.value && rows.value.length) {
      selectedName.value = rows.value[0].name;
    }
    await replaceQuery();
  } catch (error) {
    if (loadRequestId.value !== requestId) {
      return;
    }
    pageError.value =
      error instanceof Error ? error.message : "Unable to load matched rows.";
  } finally {
    if (loadRequestId.value === requestId) {
      loading.value = false;
    }
  }
}

async function updateFilter(
  field: "selectedCompany" | "selectedBankAccount" | "fromDate" | "toDate",
  value: string
) {
  if (field === "selectedCompany") {
    await store.changeCompany(value);
  } else {
    store[field] = value;
  }
  selectedName.value = "";
  await loadRows();
}

async function selectRow(name: string) {
  selectedName.value = name;
  await replaceQuery();
}

function requestUnreconcile(cancelLinkedDocuments: boolean) {
  if (!selectedRow.value) {
    return;
  }
  pendingUnreconcile.value = cancelLinkedDocuments;
}

async function confirmUnreconcile() {
  if (!selectedRow.value || pendingUnreconcile.value === null) {
    return;
  }

  const cancelLinkedDocuments = pendingUnreconcile.value;
  submittingName.value = selectedRow.value.name;
  pageError.value = "";
  try {
    await unreconcileTransaction({
      bank_transaction_name: selectedRow.value.name,
      cancel_linked_documents: cancelLinkedDocuments,
    });
    rows.value = rows.value.filter((row) => row.name !== selectedName.value);
    selectedName.value = rows.value[0]?.name || "";
    await replaceQuery();
  } catch (error) {
    pageError.value =
      error instanceof Error ? error.message : "Unable to unreconcile.";
  } finally {
    pendingUnreconcile.value = null;
    submittingName.value = "";
  }
}

onMounted(async () => {
  await store.initialize(route.query);
  const queryName = route.query.bank_transaction;
  selectedName.value = Array.isArray(queryName) ? queryName[0] || "" : queryName || "";
  await loadRows();
});
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 flex-col gap-4 lg:h-[calc(100vh-103px)] lg:overflow-hidden">
    <BankAccountFilters
      :companies="store.allowedCompanies"
      :selected-company="store.selectedCompany"
      :bank-accounts="store.bankAccounts"
      :selected-bank-account="store.selectedBankAccount"
      :from-date="store.fromDate"
      :to-date="store.toDate"
      :loading="loading || Boolean(submittingName)"
      @update:selected-company="updateFilter('selectedCompany', $event)"
      @update:selected-bank-account="updateFilter('selectedBankAccount', $event)"
      @update:from-date="updateFilter('fromDate', $event)"
      @update:to-date="updateFilter('toDate', $event)"
      @refresh="loadRows"
    />

    <ErrorState v-if="pageError" :message="pageError" />

    <div class="grid min-h-[620px] flex-1 gap-4 xl:min-h-0 xl:grid-cols-[minmax(620px,1fr)_460px]">
      <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-bank-line bg-white shadow-sm">
        <div class="border-b border-bank-line px-4 py-3">
          <div class="text-base font-semibold text-bank-ink">Matched transactions</div>
          <div class="text-sm tabular-nums text-bank-muted">{{ rows.length }} rows</div>
        </div>

        <LoadingState v-if="loading" label="Loading matched rows" />
        <EmptyState
          v-else-if="!rows.length"
          title="No matched transactions"
          detail="Matched rows appear here after reconciliation."
        />
        <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-auto">
          <table class="w-full min-w-[980px] divide-y divide-bank-line text-sm">
            <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
              <tr>
                <th class="px-4 py-3">Date</th>
                <th class="px-4 py-3">Transaction</th>
                <th class="px-4 py-3">Linked vouchers</th>
                <th class="px-4 py-3 text-right">Amount</th>
                <th class="w-12 px-4 py-3 text-right"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-bank-line bg-white">
              <tr
                v-for="row in rows"
                :key="row.name"
                class="cursor-pointer transition hover:bg-blue-50/60"
                :class="
                  row.name === selectedName
                    ? 'bg-blue-50 shadow-[inset_3px_0_0_0_#0891B2]'
                    : ''
                "
                role="button"
                tabindex="0"
                :aria-pressed="row.name === selectedName"
                @click="selectRow(row.name)"
                @keydown.enter.prevent="selectRow(row.name)"
                @keydown.space.prevent="selectRow(row.name)"
              >
                <td class="px-4 py-3 tabular-nums text-bank-muted">
                  {{ formatDate(row.date) }}
                </td>
                <td class="max-w-[320px] px-4 py-3">
                  <div class="truncate font-medium text-bank-ink">
                    {{ row.description || row.name }}
                  </div>
                  <div class="truncate text-xs text-bank-muted">
                    {{ row.reference_number || "No reference" }}
                  </div>
                </td>
                <td class="max-w-[280px] px-4 py-3">
                  <template v-if="linkedPaymentCount(row) === 1">
                    <a
                      class="inline-flex min-w-0 items-center gap-1 font-medium text-bank-accent"
                      :href="voucherUrl(linkedPaymentsForRow(row)[0])"
                      target="_blank"
                      rel="noreferrer"
                      @click.stop
                      @keydown.stop
                    >
                      <span class="truncate">
                        {{ linkedPaymentLabel(linkedPaymentsForRow(row)[0]) }}
                      </span>
                      <ExternalLink class="h-3.5 w-3.5 shrink-0" />
                    </a>
                  </template>
                  <div v-else-if="linkedPaymentCount(row) > 1" class="grid gap-1">
                    <div class="font-medium tabular-nums text-bank-ink">
                      {{ linkedVoucherCountLabel(linkedPaymentCount(row)) }}
                    </div>
                    <div class="text-xs text-bank-muted">
                      Select row to review
                    </div>
                  </div>
                  <div v-else class="text-bank-muted">
                    Not set
                  </div>
                </td>
                <td
                  class="px-4 py-3 text-right font-medium tabular-nums"
                  :class="signedAmountClass(row.amount)"
                >
                  {{ formatMoney(row.amount, row.currency || store.activeCurrency) }}
                </td>
                <td class="px-4 py-3 text-right">
                  <a
                    class="inline-flex h-8 w-8 items-center justify-center rounded-md text-bank-muted transition hover:bg-white hover:text-bank-accent"
                    :href="bankTransactionUrl(row)"
                    target="_blank"
                    rel="noreferrer"
                    title="Open bank transaction in Desk"
                    @click.stop
                    @keydown.stop
                  >
                    <ExternalLink class="h-4 w-4" />
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="flex min-h-0 flex-col rounded-lg border border-bank-line bg-white shadow-sm">
        <div class="border-b border-bank-line px-4 py-3">
          <div class="text-base font-semibold text-bank-ink">Review</div>
          <div class="truncate text-sm text-bank-muted">
            {{ selectedRow?.name || "No selection" }}
          </div>
        </div>

        <EmptyState
          v-if="!selectedRow"
          title="No matched row selected"
          detail="Select a row to inspect linked documents."
        />
        <div v-else class="bank-rec-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
          <dl class="grid gap-3">
            <div class="rounded-lg border border-bank-line p-3">
              <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
                Bank transaction
              </dt>
              <dd class="mt-1 break-words text-sm text-bank-ink">
                {{ selectedRow.name }}
              </dd>
              <a
                class="mt-2 inline-flex items-center gap-2 text-sm font-medium text-bank-accent"
                :href="bankTransactionUrl(selectedRow)"
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink class="h-4 w-4" />
                Open bank transaction
              </a>
            </div>
            <div class="rounded-lg border border-bank-line p-3">
              <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
                Amount
              </dt>
              <dd
                class="mt-1 text-sm font-semibold tabular-nums"
                :class="signedAmountClass(selectedRow.amount)"
              >
                {{ formatMoney(selectedRow.amount, selectedRow.currency || store.activeCurrency) }}
              </dd>
            </div>
          </dl>

          <div class="mt-4 rounded-lg border border-bank-line">
            <div class="border-b border-bank-line px-3 py-2 text-sm font-semibold text-bank-ink">
              Linked vouchers
            </div>
            <div v-if="!selectedLinkedPayments.length" class="px-3 py-4 text-sm text-bank-muted">
              No linked vouchers
            </div>
            <div v-else class="divide-y divide-bank-line">
              <a
                v-for="payment in selectedLinkedPayments"
                :key="`${payment.payment_document}-${payment.payment_entry}`"
                class="flex items-center justify-between gap-3 px-3 py-2 text-sm transition hover:bg-blue-50/60"
                :href="voucherUrl(payment)"
                target="_blank"
                rel="noreferrer"
              >
                <span class="min-w-0 truncate font-medium text-bank-accent">
                  {{ payment.payment_document || "Voucher" }}
                  {{ payment.payment_entry || "" }}
                </span>
                <span class="shrink-0 tabular-nums text-bank-ink">
                  {{
                    formatMoney(
                      payment.allocated_amount,
                      selectedRow.currency || store.activeCurrency
                    )
                  }}
                </span>
              </a>
            </div>
          </div>

          <div class="mt-auto grid gap-2 pt-4">
            <Button
              variant="subtle"
              :loading="submittingName === selectedRow.name"
              @click="requestUnreconcile(false)"
            >
              <template #prefix>
                <RotateCcw class="h-4 w-4" />
              </template>
              Unreconcile
            </Button>
            <Button
              theme="red"
              variant="subtle"
              :loading="submittingName === selectedRow.name"
              @click="requestUnreconcile(true)"
            >
              Cancel Linked and Unreconcile
            </Button>
          </div>
        </div>
      </section>
    </div>

    <div
      v-if="pendingUnreconcile !== null && selectedRow"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bank-rec-unreconcile-title"
    >
      <section class="w-full max-w-md rounded-lg border border-bank-line bg-white shadow-xl">
        <div class="border-b border-bank-line px-4 py-3">
          <h2 id="bank-rec-unreconcile-title" class="text-base font-semibold text-bank-ink">
            Unreconcile transaction
          </h2>
          <div class="mt-1 truncate text-sm text-bank-muted">
            {{ selectedRow.name }}
          </div>
        </div>
        <div class="px-4 py-4 text-sm text-bank-ink">
          {{ pendingUnreconcileMessage }}
        </div>
        <div class="flex justify-end gap-2 border-t border-bank-line bg-gray-50 px-4 py-3">
          <Button
            variant="subtle"
            :disabled="Boolean(submittingName)"
            @click="pendingUnreconcile = null"
          >
            Cancel
          </Button>
          <Button
            :theme="pendingUnreconcile ? 'red' : 'blue'"
            variant="solid"
            :loading="Boolean(submittingName)"
            @click="confirmUnreconcile"
          >
            {{ pendingUnreconcile ? "Cancel Linked and Unreconcile" : "Unreconcile" }}
          </Button>
        </div>
      </section>
    </div>
  </div>
</template>
