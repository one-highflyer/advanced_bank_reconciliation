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
import type {
  AccountingDimension,
  CashCodingRow,
  CreateOption,
  DimensionOption,
} from "@/types/bankRec";
import { formatDate, formatMoney, signedAmountClass } from "@/utils/format";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import RefreshCcw from "~icons/lucide/refresh-cw";
import TriangleAlert from "~icons/lucide/triangle-alert";

type ViewFilter = "all" | "uncoded" | "rule_suggested" | "errors" | "selected";

const store = useBankRecStore();
const route = useRoute();
const router = useRouter();

const rows = ref<CashCodingRow[]>([]);
const accountOptions = ref<CreateOption[]>([]);
const costCenterOptions = ref<CreateOption[]>([]);
const projectOptions = ref<CreateOption[]>([]);
const accountingDimensions = ref<AccountingDimension[]>([]);
const dimensionOptions = ref<Record<string, DimensionOption[]>>({});
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
const bulkDimensions = ref<Record<string, string>>({});
const viewFilterButtons = [
  { label: "All", value: "all" },
  { label: "Uncoded", value: "uncoded" },
  { label: "Rule suggested", value: "rule_suggested" },
  { label: "Errors", value: "errors" },
  { label: "Selected", value: "selected" },
];

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
const accountByName = computed(() =>
  Object.fromEntries(accountOptions.value.map((row) => [row.name, row]))
);
const tableMinWidth = computed(
  () => `${1120 + accountingDimensions.value.length * 180}px`
);

function defaultDimensionValues(dimensions: AccountingDimension[]) {
  return Object.fromEntries(
    dimensions.map((dimension) => [dimension.fieldname, dimension.default_value || ""])
  );
}

function normalizeCashCodingRow(
  row: CashCodingRow,
  dimensions: AccountingDimension[]
): CashCodingRow {
  return {
    ...row,
    dimensions: {
      ...defaultDimensionValues(dimensions),
      ...(row.dimensions || {}),
    },
  };
}

function dimensionLabel(dimension: AccountingDimension) {
  return dimension.label || dimension.fieldname;
}

function dimensionDatalistId(dimension: AccountingDimension) {
  return `cash-coding-dimension-${dimension.fieldname}`;
}

function dimensionOptionLabel(option: DimensionOption) {
  const displayValue = Object.entries(option).find(
    ([key, value]) => key !== "name" && typeof value === "string" && value
  )?.[1];
  return typeof displayValue === "string" ? displayValue : option.name;
}

function isProfitAndLossAccount(accountName: string) {
  return ["Income", "Expense"].includes(accountByName.value[accountName]?.root_type || "");
}

function isDimensionRequired(dimension: AccountingDimension, row: CashCodingRow) {
  return Boolean(
    dimension.mandatory_for_bs ||
      (isProfitAndLossAccount(row.account) && dimension.mandatory_for_pl)
  );
}

function missingRequiredDimension(row: CashCodingRow) {
  return accountingDimensions.value.find(
    (dimension) => isDimensionRequired(dimension, row) && !row.dimensions[dimension.fieldname]
  );
}

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
      company: store.selectedCompany || undefined,
      bank_account: store.selectedBankAccount || undefined,
      from_date: store.fromDate || undefined,
      to_date: store.toDate || undefined,
    },
  });
}

async function loadRows(options: { confirmDiscard?: boolean } = {}) {
  if (!store.selectedBankAccount) {
    rows.value = [];
    selected.value = [];
    rowErrors.value = {};
    clearDirty();
    await replaceQuery();
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
    const responseDimensions =
      response.options.accounting_dimensions || store.boot?.accounting_dimensions || [];
    accountingDimensions.value = responseDimensions;
    dimensionOptions.value = response.options.dimension_options || {};
    rows.value = response.rows.map((row) => normalizeCashCodingRow(row, responseDimensions));
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
  field: "selectedCompany" | "selectedBankAccount" | "fromDate" | "toDate",
  value: string
) {
  if (!guardDiscard()) {
    return;
  }
  if (field === "selectedCompany") {
    await store.changeCompany(value);
  } else {
    store[field] = value;
  }
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
    accountingDimensions.value.forEach((dimension) => {
      const value = bulkDimensions.value[dimension.fieldname];
      if (value) {
        row.dimensions[dimension.fieldname] = value;
      }
    });
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

  const rowMissingDimension = selectedRows.value.find((row) => missingRequiredDimension(row));
  if (rowMissingDimension) {
    const dimension = missingRequiredDimension(rowMissingDimension);
    if (!dimension) {
      return;
    }
    rowErrors.value = {
      ...rowErrors.value,
      [rowMissingDimension.transaction.name]: `${dimensionLabel(dimension)} is required.`,
    };
    pageError.value = "One or more selected rows are missing a required dimension.";
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
  <div class="flex min-h-0 w-full flex-1 flex-col gap-4 lg:h-[calc(100vh-103px)] lg:overflow-hidden">
    <BankAccountFilters
      :companies="store.allowedCompanies"
      :selected-company="store.selectedCompany"
      :bank-accounts="store.bankAccounts"
      :selected-bank-account="store.selectedBankAccount"
      :from-date="store.fromDate"
      :to-date="store.toDate"
      :loading="loading || submitting"
      @update:selected-company="updateFilter('selectedCompany', $event)"
      @update:selected-bank-account="updateFilter('selectedBankAccount', $event)"
      @update:from-date="updateFilter('fromDate', $event)"
      @update:to-date="updateFilter('toDate', $event)"
      @refresh="loadRows"
    />

    <div class="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <TriangleAlert class="h-4 w-4 shrink-0 text-amber-500" />
      Tax is not posted from cash coding.
    </div>

    <ErrorState
      v-if="pageError"
      :message="pageError"
    />

    <section class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-bank-line bg-white shadow-sm">
      <div class="grid gap-3 border-b border-bank-line p-4 sm:grid-cols-2 xl:grid-cols-4">
        <FormControl
          v-model="bulkAccount"
          variant="outline"
          size="md"
          list="cash-coding-accounts"
          placeholder="Account"
        />
        <FormControl
          v-model="bulkCostCenter"
          variant="outline"
          size="md"
          list="cash-coding-cost-centers"
          placeholder="Cost center"
        />
        <FormControl
          v-model="bulkProject"
          variant="outline"
          size="md"
          list="cash-coding-projects"
          placeholder="Project"
        />
        <FormControl
          v-for="dimension in accountingDimensions"
          :key="dimension.fieldname"
          v-model="bulkDimensions[dimension.fieldname]"
          variant="outline"
          size="md"
          :list="dimensionDatalistId(dimension)"
          :placeholder="dimensionLabel(dimension)"
        />
        <Button class="xl:justify-self-start" variant="subtle" @click="applyBulk">Apply</Button>
      </div>

      <div class="flex flex-col gap-3 border-b border-bank-line px-4 py-3 md:flex-row md:items-center md:justify-between">
        <TabButtons
          v-model="viewFilter"
          :buttons="viewFilterButtons"
        />
        <div class="flex gap-2">
          <Button variant="subtle" :loading="loading" @click="loadRows">
            <template #prefix>
              <RefreshCcw class="h-4 w-4" />
            </template>
            Refresh
          </Button>
          <Button theme="blue" variant="solid" :loading="submitting" @click="submitSelected">
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
      <div v-else class="bank-rec-scrollbar min-h-[360px] flex-1 overflow-auto lg:min-h-0">
        <table
          class="w-full table-fixed divide-y divide-bank-line text-sm"
          :style="{ minWidth: tableMinWidth }"
        >
          <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
            <tr>
              <th class="w-9 px-3 py-3"></th>
              <th class="w-24 px-3 py-3">Date</th>
              <th class="w-[18%] px-3 py-3">Transaction</th>
              <th class="w-32 px-3 py-3 text-right">Amount</th>
              <th class="w-[16%] px-3 py-3">Account</th>
              <th class="w-[18%] px-3 py-3">Contact</th>
              <th class="w-[13%] px-3 py-3">Cost center</th>
              <th class="w-[13%] px-3 py-3">Project</th>
              <th
                v-for="dimension in accountingDimensions"
                :key="dimension.fieldname"
                class="w-44 px-3 py-3"
              >
                {{ dimensionLabel(dimension) }}{{ dimension.mandatory_for_bs || dimension.mandatory_for_pl ? " *" : "" }}
              </th>
              <th class="w-[10%] px-3 py-3">Reference</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-bank-line bg-white">
            <tr
              v-for="row in visibleRows"
              :key="row.transaction.name"
              :class="
                rowErrors[row.transaction.name]
                  ? 'bg-red-50/50'
                  : selected.includes(row.transaction.name)
                    ? 'bg-bank-accent-50'
                    : ''
              "
            >
              <td class="px-3 py-3 align-top">
                <input
                  class="h-4 w-4 rounded border-bank-line text-bank-accent"
                  type="checkbox"
                  :checked="selected.includes(row.transaction.name)"
                  @change="toggleSelected(row.transaction.name, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td class="px-3 py-3 align-top tabular-nums text-bank-muted">
                {{ formatDate(row.transaction.date) }}
              </td>
              <td class="min-w-0 px-3 py-3 align-top">
                <div class="truncate font-medium text-bank-ink">
                  {{ row.transaction.description || row.transaction.name }}
                </div>
                <div class="truncate text-xs text-bank-muted">
                  {{ rowErrors[row.transaction.name] || row.transaction.bank_party_name || "No party" }}
                </div>
              </td>
              <td
                class="whitespace-nowrap px-3 py-3 text-right align-top font-medium tabular-nums"
                :class="signedAmountClass(row.transaction.amount)"
              >
                {{ formatMoney(row.transaction.amount, row.transaction.currency || store.activeCurrency) }}
              </td>
              <td class="px-3 py-3 align-top">
                <input
                  v-model="row.account"
                  class="h-9 w-full min-w-0 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-accounts"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-3 py-3 align-top">
                <div class="flex min-w-0 gap-2">
                  <select
                    v-model="row.party_type"
                    class="h-9 w-[6.75rem] shrink-0 rounded-md border border-bank-line bg-white px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                    @change="markDirty(row.transaction.name)"
                  >
                    <option value="">None</option>
                    <option value="Customer">Customer</option>
                    <option value="Supplier">Supplier</option>
                    <option value="Employee">Employee</option>
                  </select>
                  <input
                    v-model="row.party"
                    class="h-9 min-w-0 flex-1 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                    @input="markDirty(row.transaction.name)"
                  />
                </div>
              </td>
              <td class="px-3 py-3 align-top">
                <input
                  v-model="row.cost_center"
                  class="h-9 w-full min-w-0 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-cost-centers"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-3 py-3 align-top">
                <input
                  v-model="row.project"
                  class="h-9 w-full min-w-0 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  list="cash-coding-projects"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td
                v-for="dimension in accountingDimensions"
                :key="dimension.fieldname"
                class="px-3 py-3 align-top"
              >
                <input
                  v-model="row.dimensions[dimension.fieldname]"
                  class="h-9 w-full min-w-0 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  :list="dimensionDatalistId(dimension)"
                  @input="markDirty(row.transaction.name)"
                />
              </td>
              <td class="px-3 py-3 align-top">
                <input
                  v-model="row.reference_number"
                  class="h-9 w-full min-w-0 rounded-md border border-bank-line px-2 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
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
    <datalist
      v-for="dimension in accountingDimensions"
      :id="dimensionDatalistId(dimension)"
      :key="dimension.fieldname"
    >
      <option
        v-for="option in dimensionOptions[dimension.fieldname] || []"
        :key="option.name"
        :value="option.name"
      >
        {{ dimensionOptionLabel(option) }}
      </option>
    </datalist>

    <ReconcileProgressDialog
      :open="submitting"
      title="Posting cash coding"
      message="Posting valid rows and keeping failed rows visible."
    />
  </div>
</template>
