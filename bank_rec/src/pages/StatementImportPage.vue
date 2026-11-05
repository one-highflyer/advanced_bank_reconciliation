<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import { Dialog } from "frappe-ui";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import StatementColumnMapping from "@/components/StatementColumnMapping.vue";
import StatementImportPreview from "@/components/StatementImportPreview.vue";
import { useBankRecStore } from "@/stores/bankRec";
import {
  getImportContext,
  importStatement,
  prepareStatement,
  previewStatement,
  uploadStatementFile,
} from "@/services/statementImport";
import type {
  CsvEncoding,
  ImportContext,
  ImportMapping,
  PreparedStatement,
  StatementImportResult,
  StatementPreview,
  UploadedStatement,
} from "@/types/statementImport";
import {
  defaultSelectedRows,
  emptyImportMapping,
  hasRequiredMapping,
  hasSavedBankMapping,
  selectedImportRows,
} from "@/utils/statementImport";
import { formatDate, formatMoney } from "@/utils/format";
import ArrowLeft from "~icons/lucide/arrow-left";
import ArrowRight from "~icons/lucide/arrow-right";
import Check from "~icons/lucide/check";
import CircleAlert from "~icons/lucide/circle-alert";
import FileSpreadsheet from "~icons/lucide/file-spreadsheet";
import FileUp from "~icons/lucide/file-up";
import Info from "~icons/lucide/info";
import RefreshCcw from "~icons/lucide/refresh-cw";
import TriangleAlert from "~icons/lucide/triangle-alert";
import X from "~icons/lucide/x";

const store = useBankRecStore();
const route = useRoute();
const router = useRouter();
const fileInput = ref<HTMLInputElement | null>(null);
const context = ref<ImportContext | null>(null);
const prepared = ref<PreparedStatement | null>(null);
const uploaded = ref<UploadedStatement | null>(null);
const csvEncoding = ref<CsvEncoding>("utf-8");
const csvEncodingOptions = [
  { label: "UTF-8", value: "utf-8" },
  { label: "Windows-1252 (Western European)", value: "windows-1252" },
  { label: "Windows-1250 (Central European)", value: "windows-1250" },
];
const localFileSize = ref(0);
const mapping = ref<ImportMapping>(emptyImportMapping());
const pendingMapping = ref<ImportMapping | null>(null);
const preview = ref<StatementPreview | null>(null);
const reviewedMapping = ref<ImportMapping | null>(null);
const selected = ref<number[]>([]);
const result = ref<StatementImportResult | null>(null);
const step = ref(0);
const error = ref("");
const contextError = ref("");
const initializing = ref(true);
const changingAccount = ref(false);
const loadingContext = ref(false);
const uploading = ref(false);
const reading = ref(false);
const previewing = ref(false);
const submitting = ref(false);
const dragging = ref(false);
const confirmOpen = ref(false);
const duplicateConsent = ref(false);
let operationVersion = 0;
let contextVersion = 0;
let requestId = "";

const steps = ["Upload file", "Map columns", "Review & import"];
const busy = computed(
  () =>
    initializing.value ||
    changingAccount.value ||
    store.loading.bankAccounts ||
    loadingContext.value ||
    uploading.value ||
    reading.value ||
    previewing.value ||
    submitting.value
);
const hasWork = computed(() => Boolean(uploaded.value) && !result.value);
const selectedRows = computed(() =>
  selectedImportRows(preview.value?.rows || [], selected.value)
);
const selectedDuplicates = computed(() =>
  selectedRows.value.filter((row) => row.is_duplicate)
);
const canImport = computed(() =>
  Boolean(
    preview.value &&
      reviewedMapping.value &&
      selectedRows.value.length &&
      !preview.value.summary.errors &&
      !busy.value
  )
);
const companyOptions = computed(() => [
  { label: "Select company", value: "", disabled: true },
  ...store.allowedCompanies.map((company) => ({
    label: company,
    value: company,
  })),
]);
const bankOptions = computed(() => [
  { label: "Select bank account", value: "", disabled: true },
  ...store.bankAccounts.map((account) => ({
    label: account.account_name || account.name,
    value: account.name,
  })),
]);
const latestAmount = computed(() => {
  const last = context.value?.last_transaction;
  return last
    ? formatMoney(last.deposit || last.withdrawal, context.value?.currency)
    : "";
});
const fileSize = computed(() => {
  const size = localFileSize.value || uploaded.value?.file_size || 0;
  return size
    ? size >= 1024 * 1024
      ? (size / (1024 * 1024)).toFixed(1) + " MB"
      : Math.max(1, Math.round(size / 1024)) + " KB"
    : "";
});
const isCsv = computed(() => /\.csv$/i.test(uploaded.value?.file_name || ""));

function errorMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}

function discardAllowed() {
  return !hasWork.value || window.confirm("Discard this statement import?");
}

function clearReview() {
  preview.value = null;
  reviewedMapping.value = null;
  selected.value = [];
  confirmOpen.value = false;
  duplicateConsent.value = false;
  requestId = "";
}

function resetImport() {
  operationVersion++;
  uploaded.value = null;
  csvEncoding.value = "utf-8";
  prepared.value = null;
  mapping.value = emptyImportMapping();
  pendingMapping.value = null;
  localFileSize.value = 0;
  result.value = null;
  error.value = "";
  step.value = 0;
  clearReview();
  if (fileInput.value) fileInput.value.value = "";
}

async function replaceQuery() {
  await router.replace({
    path: "/import",
    query: {
      company: store.selectedCompany || undefined,
      bank_account: store.selectedBankAccount || undefined,
    },
  });
}

async function loadContext() {
  const account = store.selectedBankAccount;
  const version = ++contextVersion;
  context.value = null;
  contextError.value = "";
  if (!account) return;
  loadingContext.value = true;
  try {
    const response = await getImportContext(account);
    if (version === contextVersion && account === store.selectedBankAccount) {
      context.value = response;
    }
  } catch (reason) {
    if (version === contextVersion) {
      contextError.value = errorMessage(
        reason,
        "Unable to load the bank account."
      );
    }
  } finally {
    if (version === contextVersion) loadingContext.value = false;
  }
}

async function updateAccount(field: "company" | "bank", value: unknown) {
  if (busy.value || !discardAllowed()) return;
  changingAccount.value = true;
  try {
    resetImport();
    const version = operationVersion;
    if (field === "company") await store.changeCompany(String(value || ""));
    else store.selectedBankAccount = String(value || "");
    if (version !== operationVersion) return;
    await replaceQuery();
    if (version === operationVersion) await loadContext();
  } finally {
    changingAccount.value = false;
  }
}

async function readFile(previousMapping?: ImportMapping) {
  if (!uploaded.value || !context.value) return false;
  const version = operationVersion;
  const account = store.selectedBankAccount;
  const fileId = uploaded.value.name;
  reading.value = true;
  error.value = "";
  try {
    const response = await prepareStatement(account, fileId, csvEncoding.value);
    if (version !== operationVersion || account !== store.selectedBankAccount)
      return false;
    const next = { ...emptyImportMapping(), ...response.mapping };
    const restored = previousMapping || pendingMapping.value;
    if (restored) {
      for (const key of Object.keys(restored)) {
        const value = restored[key];
        if (key.endsWith("_select")) {
          next[key] =
            typeof value === "string" && response.headers.includes(value)
              ? value
              : "";
          if (value && !next[key]) response.stale_mappings.push(String(value));
        } else {
          next[key] = value;
        }
      }
    }
    if (!context.value?.can_save_mapping)
      next.save_mapping_for_future_use = false;
    response.stale_mappings = [...new Set(response.stale_mappings)];
    mapping.value = next;
    prepared.value = response;
    pendingMapping.value = null;
    return true;
  } catch (reason) {
    if (version === operationVersion)
      error.value = errorMessage(reason, "Unable to read this statement.");
    return false;
  } finally {
    if (version === operationVersion) reading.value = false;
  }
}

async function chooseFile(file?: File) {
  if (!file || busy.value || !context.value) return;
  if (!/\.(csv|xlsx|xls)$/i.test(file.name)) {
    error.value = "Choose a CSV, XLSX, or XLS file.";
    if (fileInput.value) fileInput.value.value = "";
    return;
  }
  const previousMapping = uploaded.value ? { ...mapping.value } : undefined;
  const version = ++operationVersion;
  clearReview();
  result.value = null;
  error.value = "";
  uploading.value = true;
  try {
    const response = await uploadStatementFile(file);
    if (version !== operationVersion) return;
    uploaded.value = response;
    csvEncoding.value = "utf-8";
    prepared.value = null;
    pendingMapping.value = previousMapping || null;
    localFileSize.value = file.size;
    await readFile(previousMapping);
  } catch (reason) {
    if (version === operationVersion)
      error.value = errorMessage(reason, "Unable to upload this file.");
  } finally {
    if (version === operationVersion) uploading.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
}

async function changeCsvEncoding(value: CsvEncoding) {
  if (busy.value || value === csvEncoding.value) return;
  if (prepared.value) pendingMapping.value = { ...mapping.value };
  csvEncoding.value = value;
  prepared.value = null;
  clearReview();
  await readFile();
}

function dropFile(event: DragEvent) {
  dragging.value = false;
  const files = event.dataTransfer?.files;
  if (files?.length && files.length > 1) {
    error.value = "Choose one bank statement at a time.";
    return;
  }
  void chooseFile(files?.[0]);
}

async function continueToMapping() {
  if (!uploaded.value || busy.value) return;
  if (prepared.value || (await readFile())) step.value = 1;
}

function updateMapping(values: Partial<ImportMapping>) {
  Object.assign(mapping.value, values);
  clearReview();
  error.value = "";
}

async function buildPreview() {
  if (!uploaded.value || busy.value || !hasRequiredMapping(mapping.value))
    return;
  const version = ++operationVersion;
  const account = store.selectedBankAccount;
  const reviewed = { ...mapping.value };
  previewing.value = true;
  error.value = "";
  clearReview();
  try {
    const response = await previewStatement(
      account,
      uploaded.value.name,
      reviewed,
      csvEncoding.value
    );
    if (version !== operationVersion || account !== store.selectedBankAccount)
      return;
    preview.value = response;
    reviewedMapping.value = reviewed;
    selected.value = defaultSelectedRows(response.rows);
    requestId = createRequestId();
    step.value = 2;
  } catch (reason) {
    if (version === operationVersion)
      error.value = errorMessage(reason, "Unable to preview this statement.");
  } finally {
    if (version === operationVersion) previewing.value = false;
  }
}

function createRequestId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, "0")
  ).join("");
}

function updateSelection(indices: number[]) {
  if (busy.value) return;
  selected.value = indices;
  duplicateConsent.value = false;
  requestId = createRequestId();
}

function editMapping() {
  if (busy.value) return;
  step.value = 1;
  clearReview();
  error.value = "";
}

function requestImport() {
  if (!canImport.value) return;
  duplicateConsent.value = false;
  confirmOpen.value = true;
}

async function submitImport() {
  if (
    !canImport.value ||
    !uploaded.value ||
    !reviewedMapping.value ||
    !preview.value
  )
    return;
  if (selectedDuplicates.value.length && !duplicateConsent.value) return;
  submitting.value = true;
  error.value = "";
  try {
    const response = await importStatement({
      bank_account: store.selectedBankAccount,
      file_id: uploaded.value.name,
      csv_encoding: csvEncoding.value,
      mapping: { ...reviewedMapping.value },
      selected_rows: [...selected.value],
      include_duplicates:
        selectedDuplicates.value.length > 0 && duplicateConsent.value,
      confirmed_duplicate_rows: selectedDuplicates.value.map(
        (row) => row.index
      ),
      file_hash: preview.value.file_hash,
      account_revision: preview.value.account_revision,
      request_id: requestId,
    });
    result.value = response;
    step.value = 3;
    confirmOpen.value = false;
  } catch (reason) {
    error.value = errorMessage(
      reason,
      "Unable to import this statement. Your file and mapping are kept."
    );
    confirmOpen.value = false;
  } finally {
    submitting.value = false;
  }
}

async function cancelImport() {
  if (busy.value || !discardAllowed()) return;
  resetImport();
  await router.push({
    path: "/reconcile",
    query: {
      company: store.selectedCompany,
      bank_account: store.selectedBankAccount,
    },
  });
}

async function goToReconcile() {
  if (!result.value) return;
  store.selectedTransactionName = "";
  await router.push({
    path: "/reconcile",
    query: {
      company: store.selectedCompany,
      bank_account: result.value.bank_account,
      from_date: result.value.from_date || undefined,
      to_date: result.value.to_date || undefined,
      status: "unreconciled",
    },
  });
}

async function importAnother() {
  resetImport();
  await loadContext();
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!hasWork.value && !submitting.value) return;
  event.preventDefault();
  event.returnValue = "";
}

onMounted(async () => {
  window.addEventListener("beforeunload", beforeUnload);
  const version = operationVersion;
  try {
    await store.initialize(route.query);
    if (version !== operationVersion) return;
    if (!store.errors.boot && !store.errors.bankAccounts) {
      await replaceQuery();
      if (version === operationVersion) await loadContext();
    }
  } finally {
    initializing.value = false;
  }
});
onBeforeUnmount(() => {
  operationVersion++;
  contextVersion++;
  window.removeEventListener("beforeunload", beforeUnload);
});
onBeforeRouteLeave(() => !submitting.value && discardAllowed());
</script>

<template>
  <div class="flex min-h-0 w-full min-w-0 flex-1 flex-col gap-4">
    <input
      ref="fileInput"
      type="file"
      accept=".csv,.xlsx,.xls"
      class="sr-only"
      aria-label="Bank statement file"
      :disabled="busy || !context"
      @change="chooseFile(($event.target as HTMLInputElement).files?.[0])"
    />
    <section
      class="rounded-lg border border-bank-line bg-bank-panel p-3 shadow-sm"
      aria-label="Import bank account"
    >
      <div
        class="grid items-end gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]"
      >
        <FormControl
          type="select"
          label="Company"
          variant="outline"
          size="md"
          :model-value="store.selectedCompany"
          :options="companyOptions"
          :disabled="busy || step > 0 || !store.allowedCompanies.length"
          @update:model-value="updateAccount('company', $event)"
        />
        <FormControl
          type="select"
          label="Bank account"
          variant="outline"
          size="md"
          :model-value="store.selectedBankAccount"
          :options="bankOptions"
          :disabled="
            busy ||
            step > 0 ||
            !store.selectedCompany ||
            !store.bankAccounts.length
          "
          @update:model-value="updateAccount('bank', $event)"
        />
        <div
          v-if="context"
          class="pb-1 text-xs text-bank-muted md:col-span-2 xl:col-span-1 xl:text-right"
        >
          <div>
            {{ context.bank || "No bank linked" }} · {{ context.currency }}
          </div>
          <div class="mt-1">
            <template v-if="context.last_transaction"
              >Latest transaction:
              {{ formatDate(context.last_transaction.date) }}</template
            >
            <template v-else>No previous transactions</template>
          </div>
        </div>
      </div>
    </section>

    <div>
      <h1 class="text-xl font-semibold tracking-tight text-bank-ink">
        Import statement
      </h1>
      <p class="mt-1 text-sm text-bank-muted">
        Upload a file, map its columns, and review the transactions.
      </p>
    </div>

    <ErrorState
      v-if="store.errors.boot || store.errors.bankAccounts"
      :message="store.errors.boot || store.errors.bankAccounts"
    />
    <LoadingState
      v-else-if="initializing || loadingContext"
      label="Loading the bank account"
    />
    <ErrorState
      v-else-if="contextError"
      :message="contextError"
      can-retry
      @retry="loadContext"
    />
    <EmptyState
      v-else-if="!context"
      title="Select a bank account"
      detail="Select the company and bank account for this statement."
    />
    <template v-else>
      <div
        v-if="error"
        class="flex flex-wrap items-start gap-3 rounded-lg border border-outline-red-1 bg-surface-red-2 p-4 text-sm text-ink-red-4"
        role="alert"
      >
        <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" />
        <div class="min-w-0 flex-1 break-words">
          {{ error }}
          <div v-if="uploaded" class="mt-1 text-xs">
            Your file and mapping are kept. No success has been reported.
          </div>
        </div>
        <Button
          v-if="step === 2"
          variant="subtle"
          :disabled="busy"
          @click="buildPreview"
        >
          <template #prefix><RefreshCcw class="h-4 w-4" /></template>
          Refresh preview
        </Button>
      </div>

      <section
        class="min-w-0 rounded-lg border border-bank-line bg-bank-panel shadow-sm"
        aria-label="Statement import"
      >
        <nav
          v-if="step < 3"
          class="grid grid-cols-3 border-b border-bank-line px-3 md:px-5"
          aria-label="Import steps"
        >
          <button
            v-for="(label, index) in steps"
            :key="label"
            type="button"
            class="flex min-w-0 items-center gap-2 border-b-2 py-4 text-left text-xs disabled:cursor-default sm:text-sm"
            :class="
              step === index
                ? 'border-bank-accent font-medium text-bank-accent'
                : 'border-transparent text-bank-muted'
            "
            :aria-current="step === index ? 'step' : undefined"
            :disabled="busy || index > step"
            @click="
              index < step
                ? index === 0
                  ? (step = 0)
                  : editMapping()
                : undefined
            "
          >
            <span
              class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs"
              :class="
                step === index
                  ? 'bg-bank-accent text-[var(--nexwave-on-primary,var(--nexwave-surface))]'
                  : 'bg-bank-muted-surface'
              "
            >
              <Check v-if="index < step" class="h-3.5 w-3.5 text-bank-accent" />
              <span v-else>{{ index + 1 }}</span>
            </span>
            <span>{{ label }}</span>
          </button>
        </nav>

        <div
          v-if="step === 0"
          class="grid gap-6 p-4 md:p-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]"
        >
          <div class="min-w-0">
            <div
              class="flex min-h-[230px] flex-col items-center justify-center gap-3 rounded-md border border-dashed p-6 text-center"
              :class="
                dragging
                  ? 'border-bank-accent bg-bank-accent-soft'
                  : 'border-bank-line bg-bank-surface'
              "
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="dropFile"
            >
              <FileUp class="h-7 w-7 text-bank-accent" />
              <div class="text-base font-semibold text-bank-ink">
                Choose your bank statement
              </div>
              <p class="text-sm text-bank-muted">
                Drop a CSV, XLSX, or XLS file here.
              </p>
              <Button
                theme="blue"
                variant="solid"
                :loading="uploading || reading"
                :disabled="busy"
                @click="fileInput?.click()"
                >{{
                  uploading
                    ? "Uploading file"
                    : reading
                    ? "Reading file"
                    : "Choose file"
                }}</Button
              >
            </div>
            <div
              v-if="uploaded"
              class="mt-4 flex items-center gap-3 rounded-md border border-bank-line p-4"
            >
              <FileSpreadsheet class="h-5 w-5 shrink-0 text-bank-accent" />
              <div class="min-w-0 flex-1">
                <div class="break-all text-sm font-medium text-bank-ink">
                  {{ uploaded.file_name }}
                </div>
                <div class="mt-1 text-xs tabular-nums text-bank-muted">
                  <template v-if="prepared"
                    >{{ prepared.row_count }} transactions · </template
                  >{{ fileSize }}
                </div>
              </div>
              <Button
                variant="ghost"
                label="Remove file"
                :disabled="busy"
                @click="resetImport"
              >
                <template #icon><X class="h-4 w-4" /></template>
              </Button>
            </div>
            <FormControl
              v-if="isCsv"
              class="mt-4 max-w-sm"
              type="select"
              label="CSV encoding"
              variant="outline"
              :model-value="csvEncoding"
              :options="csvEncodingOptions"
              :disabled="busy"
              @update:model-value="changeCsvEncoding"
            />
            <p class="mt-3 text-xs text-bank-muted">
              Review the mapped transactions before they are imported.
            </p>
          </div>
          <aside
            class="min-w-0 border-t border-bank-line pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"
          >
            <div class="text-sm font-semibold text-bank-ink">
              Selected account
            </div>
            <dl
              class="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm"
            >
              <dt class="text-bank-muted">Company</dt>
              <dd class="break-words text-right text-bank-ink">
                {{ context.bank_account.company }}
              </dd>
              <dt class="text-bank-muted">Account</dt>
              <dd class="break-words text-right text-bank-ink">
                {{ context.bank_account.account_name }}
              </dd>
              <dt class="text-bank-muted">Bank</dt>
              <dd class="break-words text-right text-bank-ink">
                {{ context.bank || "Not linked" }}
              </dd>
              <dt class="text-bank-muted">Currency</dt>
              <dd class="text-right text-bank-ink">{{ context.currency }}</dd>
            </dl>
            <div
              class="mt-5 flex items-start gap-2 rounded-md bg-bank-accent-soft p-3 text-sm text-bank-accent"
            >
              <Info class="mt-0.5 h-4 w-4 shrink-0" />
              <div v-if="context.last_transaction">
                Latest transaction
                <div class="mt-1 font-medium">
                  {{ latestAmount }}
                  {{
                    context.last_transaction.deposit ? "deposit" : "withdrawal"
                  }}
                  · {{ formatDate(context.last_transaction.date) }}
                </div>
                <p class="mt-1 text-xs">Use this date to check for overlap.</p>
              </div>
              <span v-else
                >No previous submitted transactions were found for this
                account.</span
              >
            </div>
            <p
              v-if="hasSavedBankMapping(context.bank_mapping)"
              class="mt-4 text-xs text-bank-muted"
            >
              A saved column mapping is available for this bank.
            </p>
          </aside>
        </div>

        <StatementColumnMapping
          v-else-if="step === 1 && prepared"
          :mapping="mapping"
          :prepared="prepared"
          :context="context"
          :busy="busy"
          @update="updateMapping"
        />
        <StatementImportPreview
          v-else-if="step === 2 && preview"
          :preview="preview"
          :selected="selected"
          :busy="busy"
          @select="updateSelection"
          @edit-mapping="editMapping"
        />
        <div
          v-else-if="step === 3 && result"
          class="flex min-h-[420px] flex-col items-center gap-4 px-5 py-12 text-center"
        >
          <div
            class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-green-2 text-ink-green-3"
          >
            <Check class="h-6 w-6" />
          </div>
          <h2 class="text-xl font-semibold text-bank-ink">
            Statement imported
          </h2>
          <p class="max-w-md text-sm text-bank-muted">
            {{ result.imported_count }}
            {{
              result.imported_count === 1
                ? "transaction is"
                : "transactions are"
            }}
            ready to reconcile in
            {{ context.bank_account.account_name }}.
          </p>
          <dl
            class="mt-2 grid w-full max-w-md grid-cols-[auto_minmax(0,1fr)] gap-x-5 gap-y-3 border-t border-bank-line pt-5 text-left text-sm"
          >
            <dt class="text-bank-muted">File</dt>
            <dd class="break-all text-right text-bank-ink">
              {{ uploaded?.file_name }}
            </dd>
            <dt class="text-bank-muted">Imported</dt>
            <dd class="text-right tabular-nums text-bank-ink">
              {{ result.imported_count }}
              {{ result.imported_count === 1 ? "transaction" : "transactions" }}
            </dd>
            <dt class="text-bank-muted">Not selected</dt>
            <dd class="text-right tabular-nums text-bank-ink">
              {{ result.unselected_count }}
              {{
                result.unselected_count === 1 ? "transaction" : "transactions"
              }}
            </dd>
            <dt class="text-bank-muted">Date range</dt>
            <dd class="text-right text-bank-ink">
              {{ formatDate(result.from_date || undefined) }} to
              {{ formatDate(result.to_date || undefined) }}
            </dd>
            <dt class="text-bank-muted">Column mapping</dt>
            <dd class="text-right text-bank-ink">
              {{
                result.mapping_saved
                  ? "Saved for " + context.bank
                  : "Kept for this import"
              }}
            </dd>
          </dl>
          <p
            v-for="warning in result.warnings"
            :key="warning"
            class="max-w-md text-sm text-ink-amber-3"
          >
            {{ warning }}
          </p>
        </div>

        <footer
          class="flex flex-wrap items-center justify-between gap-3 rounded-b-lg border-t border-bank-line bg-bank-muted-surface px-4 py-3 md:px-5"
        >
          <Button
            v-if="step < 3"
            variant="ghost"
            :disabled="busy"
            @click="cancelImport"
            >Cancel</Button
          >
          <span v-else class="text-xs text-bank-muted">Import complete</span>
          <div class="ml-auto flex flex-wrap justify-end gap-2">
            <template v-if="step === 0">
              <Button
                theme="blue"
                variant="solid"
                :loading="reading"
                :disabled="busy || !uploaded"
                @click="continueToMapping"
              >
                Continue to mapping
                <template #suffix><ArrowRight class="h-4 w-4" /></template>
              </Button>
            </template>
            <template v-else-if="step === 1">
              <Button variant="subtle" :disabled="busy" @click="step = 0">
                <template #prefix><ArrowLeft class="h-4 w-4" /></template>
                Back
              </Button>
              <Button
                theme="blue"
                variant="solid"
                :loading="previewing"
                :disabled="busy || !hasRequiredMapping(mapping)"
                @click="buildPreview"
              >
                Review transactions
                <template #suffix><ArrowRight class="h-4 w-4" /></template>
              </Button>
            </template>
            <template v-else-if="step === 2">
              <Button variant="subtle" :disabled="busy" @click="editMapping">
                <template #prefix><ArrowLeft class="h-4 w-4" /></template>
                Back
              </Button>
              <Button
                theme="blue"
                variant="solid"
                :disabled="!canImport"
                @click="requestImport"
                >Import {{ selectedRows.length }}
                {{
                  selectedRows.length === 1 ? "transaction" : "transactions"
                }}</Button
              >
            </template>
            <template v-else-if="step === 3">
              <Button variant="subtle" :disabled="busy" @click="importAnother"
                >Import another statement</Button
              >
              <Button theme="blue" variant="solid" @click="goToReconcile">
                Go to Reconcile
                <template #suffix><ArrowRight class="h-4 w-4" /></template>
              </Button>
            </template>
          </div>
        </footer>
      </section>
    </template>

    <Dialog
      v-model="confirmOpen"
      size="md"
      :title="
        'Import ' +
        selectedRows.length +
        (selectedRows.length === 1 ? ' transaction?' : ' transactions?')
      "
      :dismissible="!submitting"
      :show-close-button="!submitting"
    >
      <template #title
        ><h2 class="text-base font-semibold text-bank-ink">
          Import {{ selectedRows.length }}
          {{ selectedRows.length === 1 ? "transaction" : "transactions" }}?
        </h2></template
      >
      <p class="text-sm leading-6 text-bank-muted">
        The selected transactions will be added to
        {{ context?.bank_account.account_name }} for
        {{ store.selectedCompany }}.
      </p>
      <div v-if="selectedDuplicates.length" class="mt-4">
        <div
          class="flex items-start gap-2 rounded-md bg-surface-amber-2 p-3 text-sm text-ink-amber-3"
        >
          <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
          <span
            >Your selection includes {{ selectedDuplicates.length }} possible
            {{
              selectedDuplicates.length === 1 ? "duplicate" : "duplicates"
            }}.</span
          >
        </div>
        <label class="mt-4 flex items-start gap-2 text-sm text-bank-ink">
          <input
            v-model="duplicateConsent"
            type="checkbox"
            :disabled="submitting"
            class="mt-0.5 h-4 w-4 shrink-0 rounded accent-[var(--nexwave-primary)]"
          />
          <span
            >I reviewed the possible duplicates and want to import them.</span
          >
        </label>
      </div>
      <p v-else-if="preview" class="mt-3 text-xs text-bank-muted">
        {{ preview.summary.total - selectedRows.length }} unselected
        {{
          preview.summary.total - selectedRows.length === 1
            ? "transaction"
            : "transactions"
        }}
        will not be imported.
      </p>
      <p v-if="submitting" class="mt-4 text-sm text-bank-accent" role="status">
        Importing the statement. Keep this page open.
      </p>
      <template #actions>
        <div class="flex flex-wrap justify-end gap-2">
          <Button
            variant="subtle"
            :disabled="submitting"
            @click="confirmOpen = false"
            >Back to review</Button
          >
          <Button
            theme="blue"
            variant="solid"
            :loading="submitting"
            :disabled="
              submitting || (selectedDuplicates.length > 0 && !duplicateConsent)
            "
            @click="submitImport"
            >Import transactions</Button
          >
        </div>
      </template>
    </Dialog>
  </div>
</template>
