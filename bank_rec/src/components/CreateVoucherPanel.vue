<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type {
  BankTransaction,
  CreateDefaultsResponse,
  CreateVoucherPayload,
} from "@/types/bankRec";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import ExternalLink from "~icons/lucide/external-link";
import Save from "~icons/lucide/save";

const props = defineProps<{
  transaction?: BankTransaction;
  defaults: CreateDefaultsResponse | null;
  loading?: boolean;
  creating?: boolean;
  drafting?: boolean;
  error?: string;
  createError?: string;
  draftError?: string;
  draftUrl?: string;
}>();

const emit = defineEmits<{
  create: [payload: CreateVoucherPayload];
  draft: [payload: CreateVoucherPayload];
  refresh: [];
}>();

const account = ref("");
const partyType = ref("");
const party = ref("");
const modeOfPayment = ref("");
const postingDate = ref("");
const referenceDate = ref("");
const referenceNumber = ref("");
const costCenter = ref("");
const project = ref("");
const saveAsRule = ref(false);
const ruleTitle = ref("");
const validationError = ref("");

const accountOption = computed(() =>
  props.defaults?.options.accounts.find((row) => row.name === account.value)
);

const isPaymentEntryPath = computed(() => !account.value && partyType.value && party.value);
const contactLabel = computed(() =>
  props.transaction?.direction === "withdrawal" ? "Supplier" : "Customer"
);
const accountLabel = computed(() =>
  props.transaction?.direction === "withdrawal" ? "Expense account" : "Income account"
);

function payload(): CreateVoucherPayload {
  return {
    account: account.value,
    party_type: partyType.value,
    party: party.value,
    mode_of_payment: modeOfPayment.value,
    posting_date: postingDate.value,
    reference_date: referenceDate.value,
    reference_number: referenceNumber.value,
    cost_center: costCenter.value,
    project: project.value,
    save_as_rule: saveAsRule.value,
    rule_title: ruleTitle.value,
  };
}

function validate() {
  validationError.value = "";
  if (!account.value && (!partyType.value || !party.value)) {
    validationError.value = "Choose an account or contact before creating a voucher.";
    return false;
  }
  if (
    accountOption.value?.account_type &&
    ["Receivable", "Payable"].includes(accountOption.value.account_type) &&
    (!partyType.value || !party.value)
  ) {
    validationError.value = "Contact is required for receivable or payable accounts.";
    return false;
  }
  if (saveAsRule.value && !ruleTitle.value) {
    validationError.value = "Rule title is required when saving a rule.";
    return false;
  }
  return true;
}

function create() {
  if (validate()) {
    emit("create", payload());
  }
}

function draft() {
  if (validate()) {
    emit("draft", payload());
  }
}

watch(
  () => props.defaults?.transaction.name,
  () => {
    account.value = "";
    partyType.value = props.defaults?.defaults.party_type || "";
    party.value = props.defaults?.defaults.party || "";
    modeOfPayment.value = "";
    postingDate.value = props.defaults?.defaults.posting_date || "";
    referenceDate.value = props.defaults?.defaults.reference_date || "";
    referenceNumber.value = props.defaults?.defaults.reference_number || "";
    costCenter.value = "";
    project.value = "";
    saveAsRule.value = false;
    ruleTitle.value = "";
    validationError.value = "";
  },
  { immediate: true }
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex items-center justify-between gap-3 border-b border-bank-line px-4 py-3">
      <div>
        <div class="text-base font-semibold text-bank-ink">Create</div>
        <div class="text-sm text-bank-muted">
          {{ isPaymentEntryPath ? "Payment Entry" : "Journal Entry" }}
        </div>
      </div>
      <Button variant="subtle" :loading="loading" @click="$emit('refresh')">
        Refresh
      </Button>
    </div>

    <LoadingState v-if="loading" label="Loading create form" />
    <ErrorState
      v-else-if="error"
      :message="error"
      can-retry
      @retry="$emit('refresh')"
    />
    <EmptyState
      v-else-if="!transaction || !defaults"
      title="No transaction selected"
      detail="Select a bank transaction from the list."
    />

    <form v-else class="bank-rec-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto" @submit.prevent="create">
      <div class="grid gap-4 p-4 md:grid-cols-2">
        <label class="block md:col-span-2">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            {{ accountLabel }}
          </span>
          <input
            v-model="account"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            list="bank-rec-create-accounts"
            type="text"
          />
          <datalist id="bank-rec-create-accounts">
            <option
              v-for="row in defaults.options.accounts"
              :key="row.name"
              :value="row.name"
            >
              {{ row.account_name || row.name }}
            </option>
          </datalist>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Contact type
          </span>
          <select
            v-model="partyType"
            class="h-10 w-full rounded-md border border-bank-line bg-white px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          >
            <option value="">Not set</option>
            <option value="Customer">Customer</option>
            <option value="Supplier">Supplier</option>
            <option value="Employee">Employee</option>
          </select>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            {{ contactLabel }}
          </span>
          <input
            v-model="party"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="text"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Mode of payment
          </span>
          <input
            v-model="modeOfPayment"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            list="bank-rec-create-modes"
            type="text"
          />
          <datalist id="bank-rec-create-modes">
            <option
              v-for="row in defaults.options.mode_of_payments"
              :key="row.name"
              :value="row.name"
            />
          </datalist>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Posting date
          </span>
          <input
            v-model="postingDate"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="date"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Reference date
          </span>
          <input
            v-model="referenceDate"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="date"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Reference
          </span>
          <input
            v-model="referenceNumber"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="text"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Cost center
          </span>
          <input
            v-model="costCenter"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            list="bank-rec-create-cost-centers"
            type="text"
          />
          <datalist id="bank-rec-create-cost-centers">
            <option
              v-for="row in defaults.options.cost_centers"
              :key="row.name"
              :value="row.name"
            >
              {{ row.cost_center_name || row.name }}
            </option>
          </datalist>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Project
          </span>
          <input
            v-model="project"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            list="bank-rec-create-projects"
            type="text"
          />
          <datalist id="bank-rec-create-projects">
            <option
              v-for="row in defaults.options.projects"
              :key="row.name"
              :value="row.name"
            >
              {{ row.project_name || row.name }}
            </option>
          </datalist>
        </label>

        <label class="flex items-center gap-2 md:col-span-2">
          <input
            v-model="saveAsRule"
            class="h-4 w-4 rounded border-bank-line text-bank-accent"
            type="checkbox"
          />
          <span class="text-sm font-medium text-bank-ink">Save as rule</span>
        </label>

        <label v-if="saveAsRule" class="block md:col-span-2">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Rule title
          </span>
          <input
            v-model="ruleTitle"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="text"
          />
        </label>
      </div>

      <div class="mt-auto border-t border-bank-line bg-gray-50 px-4 py-3">
        <ErrorState
          v-if="validationError || createError || draftError"
          title="Unable to create"
          :message="validationError || createError || draftError || ''"
        />
        <a
          v-if="draftUrl"
          class="mb-3 inline-flex items-center gap-2 text-sm font-medium text-bank-accent"
          :href="draftUrl"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLink class="h-4 w-4" />
          Open draft in Desk
        </a>
        <div class="flex flex-col gap-2 md:flex-row md:justify-end">
          <Button variant="subtle" :loading="drafting" @click="draft">
            <template #prefix>
              <ExternalLink class="h-4 w-4" />
            </template>
            Edit in Full Page
          </Button>
          <Button theme="blue" type="submit" :loading="creating">
            <template #prefix>
              <Save class="h-4 w-4" />
            </template>
            Create and Reconcile
          </Button>
        </div>
      </div>
    </form>
  </div>
</template>
