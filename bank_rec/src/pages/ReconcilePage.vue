<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import BankAccountFilters from "@/components/BankAccountFilters.vue";
import CreateVoucherPanel from "@/components/CreateVoucherPanel.vue";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import MatchPanel from "@/components/MatchPanel.vue";
import ReconcileProgressDialog from "@/components/ReconcileProgressDialog.vue";
import StatementSummary from "@/components/StatementSummary.vue";
import TransactionDetailPanel from "@/components/TransactionDetailPanel.vue";
import TransactionList from "@/components/TransactionList.vue";
import UpdateTransactionPanel from "@/components/UpdateTransactionPanel.vue";
import { useBankRecStore } from "@/stores/bankRec";
import type { MatchVoucherSelection } from "@/types/bankRec";
import type { TransactionStatusFilter } from "@/types/bankRec";

const store = useBankRecStore();
const route = useRoute();
const router = useRouter();
const activePanel = ref<"match" | "create" | "update" | "details">("match");
const draftUrl = ref("");
const panelButtons = [
  { label: "Match", value: "match" },
  { label: "Create", value: "create" },
  { label: "Update", value: "update" },
  { label: "Details", value: "details" },
];

const hasBootError = computed(() => Boolean(store.errors.boot));
const hasBankAccountError = computed(() => Boolean(store.errors.bankAccounts));
const hasTransactionsError = computed(() => Boolean(store.errors.transactions));
const pageLoading = computed(
  () => store.loading.boot || store.loading.bankAccounts
);
const progressOpen = computed(
  () =>
    store.loading.submitMatch ||
    store.loading.createVoucher ||
    store.loading.createDraft
);
const progressTitle = computed(() => {
  if (store.loading.submitMatch) {
    return "Matching transaction";
  }
  if (store.loading.createDraft) {
    return "Preparing draft";
  }
  return "Creating voucher";
});
const progressMessage = computed(() => {
  if (store.loading.submitMatch) {
    return "Reconciling the selected transaction.";
  }
  if (store.loading.createDraft) {
    return "Saving a draft voucher for full-page editing.";
  }
  return "Creating and reconciling the selected transaction.";
});

async function replaceQuery() {
  await router.replace({
    path: route.path,
    query: store.queryState(),
  });
}

async function refresh() {
  await store.refreshReconcile();
  await Promise.all([store.loadMatchCandidates(), store.loadCreateDefaults()]);
  await replaceQuery();
}

async function selectTransaction(name: string) {
  store.selectedTransactionName = name;
  await replaceQuery();
  await store.loadSelectedContext();
  await Promise.all([store.loadMatchCandidates(), store.loadCreateDefaults()]);
}

async function updateFilter(
  field:
    | "selectedCompany"
    | "selectedBankAccount"
    | "fromDate"
    | "toDate"
    | "transactionStatus",
  value: string
) {
  if (field === "selectedCompany") {
    await store.changeCompany(value);
  } else if (field === "transactionStatus") {
    store.transactionStatus = value as TransactionStatusFilter;
  } else {
    store[field] = value;
  }

  store.selectedTransactionName = "";
  store.selectedContext = null;
  await replaceQuery();
  await refresh();
}

async function updateStatementBalance(value: string) {
  store.statementBalance = value;
  await replaceQuery();
}

async function initialize() {
  await store.initialize(route.query);
  await refresh();
}

async function submitMatch(vouchers: MatchVoucherSelection[]) {
  const response = await store.submitSelectedMatch(vouchers);
  if (response) {
    await replaceQuery();
  }
}

async function updateMetadata(payload: {
  reference_number?: string;
  party_type?: string;
  party?: string;
}) {
  const response = await store.saveTransactionMetadata(payload);
  if (response) {
    await replaceQuery();
  }
}

async function createVoucher(payload: Parameters<typeof store.createVoucher>[0]) {
  draftUrl.value = "";
  const response = await store.createVoucher(payload);
  if (response) {
    await replaceQuery();
  }
}

async function createDraft(payload: Parameters<typeof store.createDraftVoucher>[0]) {
  draftUrl.value = "";
  const response = await store.createDraftVoucher(payload);
  if (!response?.desk_url) {
    return;
  }

  const opened = window.open(response.desk_url, "_blank", "noopener");
  if (!opened) {
    draftUrl.value = response.desk_url;
  }
}

onMounted(initialize);

watch(
  () => route.query.bank_transaction,
  async (value) => {
    const selected = Array.isArray(value) ? value[0] || "" : value || "";
    if (selected === store.selectedTransactionName) {
      return;
    }

    store.selectedTransactionName = selected;
    if (!selected) {
      store.selectedContext = null;
      store.matchCandidates = [];
      store.createDefaults = null;
      return;
    }

    await store.loadSelectedContext();
    await Promise.all([store.loadMatchCandidates(), store.loadCreateDefaults()]);
  }
);
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 flex-col gap-4 lg:h-[calc(100vh-103px)] lg:overflow-hidden">
    <ErrorState
      v-if="hasBootError"
      title="Bank Rec is unavailable"
      :message="store.errors.boot"
      can-retry
      @retry="initialize"
    />

    <template v-else>
      <BankAccountFilters
        :companies="store.allowedCompanies"
        :selected-company="store.selectedCompany"
        :bank-accounts="store.bankAccounts"
        :selected-bank-account="store.selectedBankAccount"
        :from-date="store.fromDate"
        :to-date="store.toDate"
        :statement-balance="store.statementBalance"
        :status="store.transactionStatus"
        show-statement-balance
        show-status
        :loading="pageLoading || store.loading.transactions || store.loading.summary"
        @update:selected-company="updateFilter('selectedCompany', $event)"
        @update:selected-bank-account="updateFilter('selectedBankAccount', $event)"
        @update:from-date="updateFilter('fromDate', $event)"
        @update:to-date="updateFilter('toDate', $event)"
        @update:statement-balance="updateStatementBalance"
        @update:status="updateFilter('transactionStatus', $event)"
        @refresh="refresh"
      />

      <ErrorState
        v-if="hasBankAccountError"
        :message="store.errors.bankAccounts"
        can-retry
        @retry="initialize"
      />
      <EmptyState
        v-else-if="!pageLoading && !store.bankAccounts.length"
        title="No permitted bank accounts"
        detail="Ask an administrator to grant access to at least one company bank account."
      />

      <template v-else>
        <StatementSummary
          :summary="store.summary"
          :statement-balance="store.statementBalance"
          :currency="store.activeCurrency"
          :loading="store.loading.summary"
        />

        <div class="grid min-h-[620px] flex-1 gap-4 xl:min-h-0 xl:grid-cols-[minmax(380px,0.8fr)_minmax(620px,1.2fr)]">
          <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-bank-line bg-white shadow-sm">
            <div class="flex items-center justify-between gap-3 border-b border-bank-line px-4 py-3">
              <div>
                <div class="text-base font-semibold text-bank-ink">
                  Bank transactions
                </div>
                <div class="text-sm tabular-nums text-bank-muted">
                  {{ store.transactions.length }} rows
                </div>
              </div>
            </div>

            <LoadingState
              v-if="store.loading.transactions"
              label="Loading transactions"
            />
            <ErrorState
              v-else-if="hasTransactionsError"
              :message="store.errors.transactions"
              can-retry
              @retry="store.loadTransactions"
            />
            <EmptyState
              v-else-if="!store.transactions.length"
              title="No transactions found"
              detail="Change the date range, bank account, or status filter."
            />
            <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-y-auto">
              <TransactionList
                :transactions="store.transactions"
                :selected-name="store.selectedTransactionName"
                :currency="store.activeCurrency"
                @select="selectTransaction"
              />
            </div>
          </section>

          <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-bank-line bg-white shadow-sm">
            <div class="border-b border-bank-line px-4 py-3">
              <div class="truncate text-base font-semibold text-bank-ink">
                {{ store.selectedTransaction?.description || store.selectedTransaction?.name || "No transaction selected" }}
              </div>
              <div class="mt-1 overflow-x-auto">
                <TabButtons
                  v-model="activePanel"
                  :buttons="panelButtons"
                />
              </div>
            </div>

            <MatchPanel
              v-if="activePanel === 'match'"
              :transaction="store.selectedTransaction"
              :candidates="store.matchCandidates"
              :loading="store.loading.matchCandidates"
              :submitting="store.loading.submitMatch"
              :error="store.errors.matchCandidates"
              :submit-error="store.errors.submitMatch"
              :currency="store.activeCurrency"
              @refresh="store.loadMatchCandidates"
              @submit="submitMatch"
            />
            <CreateVoucherPanel
              v-else-if="activePanel === 'create'"
              :transaction="store.selectedTransaction"
              :defaults="store.createDefaults"
              :loading="store.loading.createDefaults"
              :creating="store.loading.createVoucher"
              :drafting="store.loading.createDraft"
              :error="store.errors.createDefaults"
              :create-error="store.errors.createVoucher"
              :draft-error="store.errors.createDraft"
              :draft-url="draftUrl"
              @refresh="store.loadCreateDefaults"
              @create="createVoucher"
              @draft="createDraft"
            />
            <UpdateTransactionPanel
              v-else-if="activePanel === 'update'"
              :transaction="store.selectedTransaction"
              :submitting="store.loading.updateMetadata"
              :error="store.errors.updateMetadata"
              @submit="updateMetadata"
            />
            <TransactionDetailPanel
              v-else
              embedded
              :transaction="store.selectedTransaction"
              :context="store.selectedContext"
              :bank-account="store.selectedBankAccountDoc"
              :currency="store.activeCurrency"
              :loading="store.loading.context"
              :error="store.errors.context"
              @retry="store.loadSelectedContext"
            />
          </section>
        </div>
      </template>
    </template>

    <ReconcileProgressDialog
      :open="progressOpen"
      :title="progressTitle"
      :message="progressMessage"
    />
  </div>
</template>
