<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import BankAccountFilters from "@/components/BankAccountFilters.vue";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import ReconcileProgressDialog from "@/components/ReconcileProgressDialog.vue";
import { getCashCodingRows, submitCashCoding } from "@/services/api";
import { useBankRecStore } from "@/stores/bankRec";
import type { CashCodingRow, CreateOption } from "@/types/bankRec";
import { formatDate, formatMoney } from "@/utils/format";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import RefreshCcw from "~icons/lucide/refresh-cw";

type ViewFilter = "all" | "uncoded" | "rule_suggested" | "errors" | "selected";

const store = useBankRecStore();
const route = useRoute();
const router = useRouter();

const rows = ref<CashCodingRow[]>([]);
const accountOptions = ref<CreateOption[]>([]);
const costCenterOptions = ref<CreateOption[]>([]);
const projectOptions = ref<CreateOption[]>([]);
const selected = ref<string[]>([]);
const dirtyRows = ref<Set<string>>(new Set());
const rowErrors = ref<Record<string, string>>({});
const loading = ref(false);
const submitting = ref(false);
const loadRequestId = ref(0);
const pageError = ref("");
const viewFilter = ref<ViewFilter>("all");
const bulkAccount = ref("");
const bulkCostCenter = ref("");
const bulkProject = ref("");

const visibleRows = computed(() => {
  if (viewFilter.value === "selected") {
    return rows.value.filter((row) => selected.value.includes(row.transaction.name));
  }
  if (viewFilter.value === "errors") {
    return rows.value.filter((row) => rowErrors.value[row.transaction.name]);
  }
  if (viewFilter.value === "rule_suggested") {
    return rows.value.filter((row) => row.suggested_rule);
  }
  if (viewFilter.value === "uncoded") {
    return rows.value.filter((row) => !row.account);
  }
  return rows.value;
});

const selectedRows = computed(() =>
  rows.value.filter((row) => selected.value.includes(row.transaction.name))
);

const hasDirtyRows = computed(() => dirtyRows.value.size > 0);

function markDirty(name: string) {
  const next = new Set(dirtyRows.value);
  next.add(name);
  dirtyRows.value = next;
}

function clearDirty(names?: string[]) {
  if (!names) {
    dirtyRows.value = new Set();
    return;
  }
  const next = new Set(dirtyRows.value);
  names.forEach((name) => next.delete(name));
  dirtyRows.value = next;
}

function guardDiscard() {
  if (!hasDirtyRows.value) {
    return true;
  }
  return window.confirm("Discard unsaved cash coding changes?");
}

async function replaceQuery() {
  await router.replace({
    path: route.path,
    query: {
      bank_account: store.selectedBankAccount || undefined,
      from_date: store.fromDate || undefined,
      to_date: store.toDate || undefined,
    },
  });
}

async function loadRows(options: { confirmDiscard?: boolean } = {}) {
  if (!store.selectedBankAccount) {
    return;
  }

  if (options.confirmDiscard !== false && !guardDiscard()) {
    return;
  }

  const requestId = Date.now();
  loadRequestId.value = requestId;
  loading.value = true;
  pageError.value = "";
  selected.value = [];
  rowErrors.value = {};

  try {
    const response = await getCashCodingRows({
      bank_account: store.selectedBankAccount,
      from_date: store.fromDate,
      to_date: store.toDate,
    });
    if (loadRequestId.value !== requestId) {
      return;
    }
    rows.value = response.rows;
    accountOptions.value = response.options.accounts;
    costCenterOptions.value = response.options.cost_centers;
    projectOptions.value = response.options.projects;
    clearDirty();
    await replaceQuery();
  } catch (error) {
    if (loadRequestId.value !== requestId) {
      return;
    }
    pageError.value =
      error instanceof Error ? error.message : "Unable to load cash coding rows.";
  } finally {
    if (loadRequestId.value === requestId) {
      loading.value = false;
    }
  }
}

async function updateFilter(
  field: "selectedBankAccount" | "fromDate" | "toDate",
  value: string
) {
  if (!guardDiscard()) {
    return;
  }
  store[field] = value;
  await loadRows({ confirmDiscard: false });
}

function toggleSelected(name: string, checked: boolean) {
  if (checked && !selected.value.includes(name)) {
    selected.value = [...selected.value, name];
  }
  if (!checked) {
    selected.value = selected.value.filter((rowName) => rowName !== name);
  }
}

function applyBulk() {
  pageError.value = "";
  if (!selectedRows.value.length) {
    pageError.value = "Select at least one row.";
    return;
  }

  const directions = new Set(selectedRows.value.map((row) => row.transaction.direction));
  if (bulkAccount.value && directions.size > 1) {
    pageError.value = "Account cannot be bulk-applied to mixed money directions.";
    return;
  }

  selectedRows.value.forEach((row) => {
    if (bulkAccount.value) {
      row.account = bulkAccount.value;
    }
    if (bulkCostCenter.value) {
      row.cost_center = bulkCostCenter.value;
    }
    if (bulkProject.value) {
      row.project = bulkProject.value;
    }
    markDirty(row.transaction.name);
  });
}

async function submitSelected() {
  pageError.value = "";
  if (!selectedRows.value.length) {
    pageError.value = "Select at least one row.";
    return;
  }

  const missingAccount = selectedRows.value.find((row) => !row.account);
  if (missingAccount) {
    rowErrors.value = {
      ...rowErrors.value,
      [missingAccount.transaction.name]: "Account is required.",
    };
    pageError.value = "One or more selected rows are missing an account.";
    return;
  }

  submitting.value = true;
  try {
    const response = await submitCashCoding(
      selectedRows.value.map((row) => ({
        ...row,
        bank_transaction_name: row.transaction.name,
      }))
    );

    const successNames = response.results
      .filter((result) => result.status === "success")
      .map((result) => result.bank_transaction);
    const errors = { ...rowErrors.value };
    response.results.forEach((result) => {
      if (result.status === "error") {
        errors[result.bank_transaction] = result.message;
      }
    });
    rowErrors.value = errors;
    rows.value = rows.value.filter((row) => !successNames.includes(row.transaction.name));
    selected.value = selected.value.filter((name) => !successNames.includes(name));
    clearDirty(successNames);
    await store.loadBankAccounts();
  } catch (error) {
    pageError.value =
      error instanceof Error ? error.message : "Unable to submit cash coding.";
  } finally {
    submitting.value = false;
  }
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!hasDirtyRows.value) {
    return;
  }
  event.preventDefault();
  event.returnValue = "";
}

onMounted(async () => {
  await store.initialize(route.query);
  await loadRows();
  window.addEventListener("beforeunload", beforeUnload);
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnload);
});

onBeforeRouteLeave(() => guardDiscard());
</script>

<template>
  <div class="flex min-h-0 w-full flex-col gap-4">
    <BankAccountFilters
      :bank-accounts="store.bankAccounts"
      :selected-bank-account="store.selectedBankAccount"
      :from-date="store.fromDate"
      :to-date="store.toDate"
      :loading="loading || submitting"
      @update:selected-bank-account="updateFilter('selectedBankAccount', $event)"
      @update:from-date="updateFilter('fromDate', $event)"
      @update:to-date="updateFilter('toDate', $event)"
      @refresh="loadRows"
    />

    <div class="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      Tax is not posted from cash coding.
    </div>

    <ErrorState
      v-if="pageError"
      :message="pageError"
    />

    <section class="rounded-lg border border-bank-line bg-white shadow-sm">
      <div class="grid gap-3 border-b border-bank-line p-4 lg:grid-cols-[1fr_1fr_1fr_auto]">
        <input
          v-model="bulkAccount"
          class="h-10 rounded-md border border-bank-line px-3 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          list="cash-coding-accounts"
          placeholder="Account"
        />
        <input
          v-model="bulkCostCenter"
          class="h-10 rounded-md border border-bank-line px-3 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          list="cash-coding-cost-centers"
          placeholder="Cost center"
        />
        <input
          v-model="bulkProject"
          class="h-10 rounded-md border border-bank-line px-3 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          list="cash-coding-projects"
          placeholder="Project"
        />
        <Button variant="subtle" @click="applyBulk">Apply</Button>
      </div>

      <div class="flex flex-col gap-3 border-b border-bank-line px-4 py-3 md:flex-row md:items-center md:justify-between">
        <div class="flex flex-wrap gap-1">
          <button
            v-for="filter in ['all', 'uncoded', 'rule_suggested', 'errors', 'selected']"
            :key="filter"
            class="h-8 rounded-md px-3 text-sm font-medium capitalize transition"
            :class="viewFilter === filter ? 'bg-gray-900 text-white' : 'bg-gray-100 text-bank-muted hover:text-bank-ink'"
            @click="viewFilter = filter as ViewFilter"
          >
            {{ filter.replace('_', ' ') }}
          </button>
        </div>
        <div class="flex gap-2">
          <Button variant="subtle" :loading="loading" @click="loadRows">
            <template #prefix>
              <RefreshCcw class="h-4 w-4" />
            </template>
            Refresh
          </Button>
          <Button theme="blue" :loading="submitting" @click="submitSelected">
            <template #prefix>
              <CheckCircle2 class="h-4 w-4" />
            </template>
            Submit
          </Button>
        </div>
      </div>

      <LoadingState v-if="loading" label="Loading cash coding rows" />
      <EmptyState
        v-else-if="!visibleRows.length"
        title="No cash coding rows"
        detail="Change filters or date range."
      />
      <div v-else class="bank-rec-scrollbar max-h-[720px] overflow-auto">
        <table class="min-w-[1180px] divide-y divide-bank-line text-sm">
          <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
            <tr>
              <th class="w-10 px-4 py-3"></th>
              <th class="px-4 py-3">Date</th>
              <th class="px-4 py-3">Transaction</th>
              <th class="px-4 py-3 text-right">Amount</th>
              <th class="px-4 py-3">Account</th>
              <th class="px-4 py-3">Contact</th>
              <th class="px-4 py-3">Cost center</th>
              <th class="px-4 py-3">Project</th>
              <th class="px-4 py-3">Reference</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-bank-line bg-white">
            <tr
              v-for="row in visibleRows"
              :key="row.transaction.name"
              :class="rowErrors[row.transaction.name] ? 'bg-red-50/50' : ''"
            >
              <td class="px-4 py-3 align-top">
                <input
                  class="h-4 w-4 rounded border-bank-line text-bank-accent"
                  type="checkbox"
                  :checked="selected.includes(row.transaction.name)"
                  @change="toggleSelected(row.transaction.name, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td class="px-4 py-3 align-top text-bank-muted">
                {{ formatDate(row.transaction.date) }}
              </td>
              <td class="max-w-[260px] px-4 py-3 align-top">
                <div class="truncate font-medium text-bank-ink">
                  {{ row.transaction.description || row.transaction.name }}
                </div>
                <div class="truncate text-xs text-bank-muted">
                  {{ rowErrors[row.transaction.name] || row.transaction.bank_party_name || "No party" }}
                </div>
              </td>
              <td class="px-4 py-3 text-right align-top font-medium text-bank-ink">
                {{ formatMoney(row.transaction.amount, row.transaction.currency || store.activeCurrency) }}
              </td>
              <td class="px-4 py-3 align-top">
                <input
                  v-model="row.account"
                  class="h-9 w-52 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-accounts"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-4 py-3 align-top">
                <div class="flex gap-2">
                  <select
                    v-model="row.party_type"
                    class="h-9 w-28 rounded-md border border-bank-line bg-white px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                    @change="markDirty(row.transaction.name)"
                  >
                    <option value="">None</option>
                    <option value="Customer">Customer</option>
                    <option value="Supplier">Supplier</option>
                    <option value="Employee">Employee</option>
                  </select>
                  <input
                    v-model="row.party"
                    class="h-9 w-40 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                    @input="markDirty(row.transaction.name)"
                  />
                </div>
              </td>
              <td class="px-4 py-3 align-top">
                <input
                  v-model="row.cost_center"
                  class="h-9 w-44 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-cost-centers"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-4 py-3 align-top">
                <input
                  v-model="row.project"
                  class="h-9 w-44 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-projects"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-4 py-3 align-top">
                <input
                  v-model="row.reference_number"
                  class="h-9 w-40 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <datalist id="cash-coding-accounts">
      <option v-for="row in accountOptions" :key="row.name" :value="row.name">
        {{ row.account_name || row.name }}
      </option>
    </datalist>
    <datalist id="cash-coding-cost-centers">
      <option v-for="row in costCenterOptions" :key="row.name" :value="row.name">
        {{ row.cost_center_name || row.name }}
      </option>
    </datalist>
    <datalist id="cash-coding-projects">
      <option v-for="row in projectOptions" :key="row.name" :value="row.name">
        {{ row.project_name || row.name }}
      </option>
    </datalist>

    <ReconcileProgressDialog
      :open="submitting"
      title="Posting cash coding"
      message="Posting valid rows and keeping failed rows visible."
    />
  </div>
</template>
