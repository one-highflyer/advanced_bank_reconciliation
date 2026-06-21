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
import type { BankTransaction } from "@/types/bankRec";
import { formatDate, formatMoney } from "@/utils/format";
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

const selectedRow = computed(() =>
  rows.value.find((row) => row.name === selectedName.value)
);

function voucherUrl(row: BankTransaction) {
  if (!row.payment_document || !row.payment_entry) {
    return "";
  }
  return `/app/${row.payment_document.toLowerCase().replaceAll(" ", "-")}/${row.payment_entry}`;
}

async function replaceQuery() {
  await router.replace({
    path: route.path,
    query: {
      bank_account: store.selectedBankAccount || undefined,
      from_date: store.fromDate || undefined,
      to_date: store.toDate || undefined,
      bank_transaction: selectedName.value || undefined,
    },
  });
}

async function loadRows() {
  if (!store.selectedBankAccount) {
    return;
  }

  loading.value = true;
  pageError.value = "";
  try {
    const response = await getMatchedTransactions({
      bank_account: store.selectedBankAccount,
      from_date: store.fromDate,
      to_date: store.toDate,
    });
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
    pageError.value =
      error instanceof Error ? error.message : "Unable to load matched rows.";
  } finally {
    loading.value = false;
  }
}

async function updateFilter(
  field: "selectedBankAccount" | "fromDate" | "toDate",
  value: string
) {
  store[field] = value;
  selectedName.value = "";
  await loadRows();
}

async function selectRow(name: string) {
  selectedName.value = name;
  await replaceQuery();
}

async function unreconcile(cancelLinkedDocuments: boolean) {
  if (!selectedRow.value) {
    return;
  }

  const message = cancelLinkedDocuments
    ? "Unreconcile this transaction and cancel linked Payment Entry or Journal Entry documents?"
    : "Unreconcile this transaction and keep linked documents submitted?";
  if (!window.confirm(message)) {
    return;
  }

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
  <div class="flex min-h-0 w-full flex-col gap-4">
    <BankAccountFilters
      :bank-accounts="store.bankAccounts"
      :selected-bank-account="store.selectedBankAccount"
      :from-date="store.fromDate"
      :to-date="store.toDate"
      :loading="loading || Boolean(submittingName)"
      @update:selected-bank-account="updateFilter('selectedBankAccount', $event)"
      @update:from-date="updateFilter('fromDate', $event)"
      @update:to-date="updateFilter('toDate', $event)"
      @refresh="loadRows"
    />

    <ErrorState v-if="pageError" :message="pageError" />

    <div class="grid min-h-[620px] gap-4 xl:grid-cols-[minmax(520px,1fr)_420px]">
      <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-bank-line bg-white shadow-sm">
        <div class="border-b border-bank-line px-4 py-3">
          <div class="text-base font-semibold text-bank-ink">Matched transactions</div>
          <div class="text-sm text-bank-muted">{{ rows.length }} rows</div>
        </div>

        <LoadingState v-if="loading" label="Loading matched rows" />
        <EmptyState
          v-else-if="!rows.length"
          title="No matched transactions"
          detail="Matched rows appear here after reconciliation."
        />
        <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-auto">
          <table class="min-w-[900px] divide-y divide-bank-line text-sm">
            <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
              <tr>
                <th class="px-4 py-3">Date</th>
                <th class="px-4 py-3">Transaction</th>
                <th class="px-4 py-3">Voucher</th>
                <th class="px-4 py-3 text-right">Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-bank-line bg-white">
              <tr
                v-for="row in rows"
                :key="row.name"
                class="cursor-pointer transition hover:bg-blue-50/60"
                :class="row.name === selectedName ? 'bg-blue-50' : ''"
                @click="selectRow(row.name)"
              >
                <td class="px-4 py-3 text-bank-muted">
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
                  <div class="truncate text-bank-ink">
                    {{ row.payment_document || "Voucher" }}
                  </div>
                  <div class="truncate text-xs text-bank-muted">
                    {{ row.payment_entry || "Not set" }}
                  </div>
                </td>
                <td class="px-4 py-3 text-right font-medium text-bank-ink">
                  {{ formatMoney(row.amount, row.currency || store.activeCurrency) }}
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
        <div v-else class="flex flex-1 flex-col p-4">
          <dl class="grid gap-3">
            <div class="rounded-lg border border-bank-line p-3">
              <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
                Voucher
              </dt>
              <dd class="mt-1 break-words text-sm text-bank-ink">
                {{ selectedRow.payment_document || "Not set" }}
                {{ selectedRow.payment_entry || "" }}
              </dd>
            </div>
            <div class="rounded-lg border border-bank-line p-3">
              <dt class="text-xs font-medium uppercase tracking-wide text-bank-muted">
                Amount
              </dt>
              <dd class="mt-1 text-sm font-semibold text-bank-ink">
                {{ formatMoney(selectedRow.amount, selectedRow.currency || store.activeCurrency) }}
              </dd>
            </div>
          </dl>

          <a
            v-if="voucherUrl(selectedRow)"
            class="mt-4 inline-flex items-center gap-2 text-sm font-medium text-bank-accent"
            :href="voucherUrl(selectedRow)"
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink class="h-4 w-4" />
            Open voucher
          </a>

          <div class="mt-auto grid gap-2 pt-4">
            <Button
              variant="subtle"
              :loading="submittingName === selectedRow.name"
              @click="unreconcile(false)"
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
              @click="unreconcile(true)"
            >
              Cancel Linked and Unreconcile
            </Button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
